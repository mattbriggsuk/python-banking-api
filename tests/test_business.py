from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest

from banking.business.access import AccessServiceImpl
from banking.business.account import AccountServiceImpl
from banking.business.customer import CustomerServiceImpl
from banking.domain.enums import TransactionType
from banking.domain.exceptions import (
    AccessDenied,
    AuthenticationError,
    Conflict,
    InvalidArgument,
    NotFound,
)
from banking.domain.models import Customer, Transaction, UserSession
from banking.repository.account import InMemoryAccountRepository
from banking.repository.customer import InMemoryCustomerRepository
from banking.repository.session import InMemorySessionRepository
from banking.utils.numbers import generate_number
from banking.utils.pins import hash_pin, matches_pin


@pytest.fixture
def banking():
    customers = InMemoryCustomerRepository()
    accounts = InMemoryAccountRepository()
    customer = customers.save(
        Customer(generate_number(), "Alice", "Smith", "alice@example.com"), "hash"
    )
    session = UserSession(customer, "token")
    service = AccountServiceImpl(accounts, customers)
    return service, accounts, customers, session


def test_registration_stores_only_hash_and_returns_normalised_details():
    customers = InMemoryCustomerRepository()
    service = CustomerServiceImpl(customers, InMemoryAccountRepository())
    registration = service.register(Customer(None, " Alice ", " Smith ", " ALICE@Example.com "))
    stored_hash = customers.get_pin_hash(registration.customer.customer_number)
    assert stored_hash != registration.pin
    assert matches_pin(registration.pin, stored_hash)
    assert registration.customer.first_name == "Alice"
    assert registration.customer.email == "alice@example.com"
    with pytest.raises(Conflict):
        service.register(Customer(None, "Other", "Name", "ALICE@example.com"))
    assert customers.get_pin_hash(registration.customer.customer_number) == stored_hash


@pytest.mark.parametrize("customer", [None, Customer(None, " ", "Smith", "a@example.com")])
def test_registration_rejects_missing_details_without_writing(customer):
    customers = Mock()
    service = CustomerServiceImpl(customers, Mock())
    with pytest.raises(InvalidArgument):
        service.register(customer)
    customers.save.assert_not_called()


def test_customer_lookup_validates_before_repository_and_enforces_ownership():
    customers, accounts = Mock(), Mock()
    service = CustomerServiceImpl(customers, accounts)
    customer = Customer(generate_number(), "Alice", "Smith", "a@example.com")
    session = UserSession(customer, "token")
    with pytest.raises(InvalidArgument):
        service.get_customer(session, "invalid")
    customers.get_customer.assert_not_called()
    with pytest.raises(AccessDenied):
        service.get_customer(session, generate_number())
    customers.get_customer.return_value = None
    with pytest.raises(NotFound):
        service.get_customer_accounts(session, customer.customer_number)
    accounts.get_customer_accounts.assert_not_called()


def test_session_expiry_leading_zero_pin_and_logout():
    customers = InMemoryCustomerRepository()
    sessions = InMemorySessionRepository()
    customer = customers.save(
        Customer(generate_number(), "Alice", "Smith", "a@example.com"), hash_pin("012345")
    )
    now = datetime(2026, 10, 13, tzinfo=UTC)
    access = AccessServiceImpl(customers, sessions, clock=lambda: now)
    session = access.login(customer.customer_number, "012345")
    assert access.authenticated_session(f"Bearer {session.session_token}") == session
    now += timedelta(minutes=30)
    with pytest.raises(AuthenticationError):
        access.authenticated_session(f"Bearer {session.session_token}")
    assert sessions.get(session.session_token) is None
    next_session = access.login(" A@EXAMPLE.COM ", "012345")
    access.logout(next_session)
    with pytest.raises(AuthenticationError):
        access.authenticated_session(f"Bearer {next_session.session_token}")


def test_transfer_failure_keeps_both_balances_unchanged(banking):
    service, accounts, _, session = banking
    source = service.create(session)
    target = service.create(session)
    deposit = Transaction(TransactionType.DEPOSIT, Decimal("10.00"), source.account_number)
    service.deposit(session, deposit)
    assert deposit.transaction_date.tzinfo == UTC
    instruction = Transaction(
        TransactionType.TRANSFER, Decimal("11.00"), target.account_number, source.account_number
    )
    with pytest.raises(Conflict, match="Insufficient funds"):
        service.transfer(session, instruction)
    assert accounts.get_account(source.account_number).balance == Decimal("10.00")
    assert accounts.get_account(target.account_number).balance == Decimal("0.00")
    accounts.save(replace(target, closed=True))
    instruction.amount = Decimal("1.00")
    with pytest.raises(Conflict, match="Account is closed"):
        service.transfer(session, instruction)
    assert accounts.get_account(source.account_number).balance == Decimal("10.00")


def test_rejected_repository_write_does_not_mutate_stored_snapshot(banking, monkeypatch):
    service, accounts, _, session = banking
    account = service.create(session)

    def reject(updated):
        raise RuntimeError("write rejected")

    monkeypatch.setattr(accounts, "save", reject)
    with pytest.raises(RuntimeError, match="write rejected"):
        service.deposit(
            session, Transaction(TransactionType.DEPOSIT, Decimal("1.00"), account.account_number)
        )
    assert accounts.get_account(account.account_number).balance == Decimal("0.00")


def test_rejected_transfer_write_keeps_both_snapshots(banking, monkeypatch):
    service, accounts, _, session = banking
    source, target = service.create(session), service.create(session)
    service.deposit(
        session, Transaction(TransactionType.DEPOSIT, Decimal("10.00"), source.account_number)
    )

    def reject(from_account, to_account):
        raise RuntimeError("write rejected")

    monkeypatch.setattr(accounts, "transfer_balance", reject)
    with pytest.raises(RuntimeError, match="write rejected"):
        service.transfer(
            session,
            Transaction(
                TransactionType.TRANSFER,
                Decimal("1.00"),
                target.account_number,
                source.account_number,
            ),
        )
    assert accounts.get_account(source.account_number).balance == Decimal("10.00")
    assert accounts.get_account(target.account_number).balance == Decimal("0.00")


def test_account_creation_rejects_missing_customer_without_write():
    customers = InMemoryCustomerRepository()
    accounts = InMemoryAccountRepository()
    session = UserSession(Customer(generate_number(), "Alice", "Smith", "a@example.com"), "token")
    with pytest.raises(NotFound, match="Customer not found"):
        AccountServiceImpl(accounts, customers).create(session)
    assert accounts.get_customer_accounts(session.customer_number) == []


def test_concurrent_deposits_across_services_share_repository_lock(banking):
    service, accounts, customers, session = banking
    second_service = AccountServiceImpl(accounts, customers)
    account = service.create(session)

    def deposit(index):
        selected = service if index % 2 else second_service
        selected.deposit(
            session, Transaction(TransactionType.DEPOSIT, Decimal("0.01"), account.account_number)
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(deposit, range(200)))
    assert accounts.get_account(account.account_number).balance == Decimal("2.00")
    assert account.balance == Decimal("0.00")


def test_concurrent_transfers_conserve_total(banking):
    service, accounts, _, session = banking
    source, target = service.create(session), service.create(session)
    service.deposit(
        session, Transaction(TransactionType.DEPOSIT, Decimal("100.00"), source.account_number)
    )

    def transfer(_):
        service.transfer(
            session,
            Transaction(
                TransactionType.TRANSFER,
                Decimal("0.01"),
                target.account_number,
                source.account_number,
            ),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(transfer, range(200)))
    assert accounts.get_account(source.account_number).balance == Decimal("98.00")
    assert accounts.get_account(target.account_number).balance == Decimal("2.00")
