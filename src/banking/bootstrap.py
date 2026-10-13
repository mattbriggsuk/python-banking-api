"""Composition root: the only place that selects concrete adapters and services."""

from dataclasses import dataclass

from banking.business.access import AccessServiceImpl
from banking.business.account import AccountServiceImpl
from banking.business.customer import CustomerServiceImpl
from banking.domain.services import AccessService, AccountService, CustomerService
from banking.repository.account import InMemoryAccountRepository
from banking.repository.customer import InMemoryCustomerRepository
from banking.repository.session import InMemorySessionRepository


@dataclass(frozen=True, slots=True)
class Services:
    access: AccessService
    accounts: AccountService
    customers: CustomerService


def build_services() -> Services:
    customers = InMemoryCustomerRepository()
    accounts = InMemoryAccountRepository()
    sessions = InMemorySessionRepository()
    return Services(
        access=AccessServiceImpl(customers, sessions),
        accounts=AccountServiceImpl(accounts, customers),
        customers=CustomerServiceImpl(customers, accounts),
    )
