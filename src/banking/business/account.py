from dataclasses import replace

from banking.domain.enums import AccountType, TransactionType
from banking.domain.exceptions import AccessDenied, Conflict, InvalidArgument, NotFound
from banking.domain.models import Account, Transaction, TransferResult, UserSession
from banking.domain.repositories import AccountRepository, CustomerRepository
from banking.utils.clock import utc_now
from banking.utils.numbers import generate_number, is_valid_number
from banking.utils.validation import add_money, require_funds, validate_transaction


class AccountServiceImpl:
    def __init__(self, accounts: AccountRepository, customers: CustomerRepository) -> None:
        self._accounts = accounts
        self._customers = customers

    def create(
        self, session: UserSession, account_type: AccountType = AccountType.CURRENT
    ) -> Account:
        if not isinstance(account_type, AccountType):
            raise InvalidArgument("Account type must be CURRENT, SAVINGS or CREDIT")
        with self._accounts.transaction():
            if self._customers.get_customer(session.customer_number) is None:
                raise NotFound("Customer not found")
            number = generate_number()
            while self._accounts.get_account(number) is not None:
                number = generate_number()
            return self._accounts.save(
                Account(number, session.customer_number, account_type=account_type)
            )

    def close(self, session: UserSession, account_number: str) -> Account:
        with self._accounts.transaction():
            account = self._get_owned_account(session, account_number)
            if account.balance != 0:
                raise Conflict("Account balance must be zero before closing")
            return self._accounts.save(replace(account, closed=True))

    def deposit(self, session: UserSession, transaction: Transaction) -> Account:
        validate_transaction(transaction, TransactionType.DEPOSIT)
        transaction.transaction_date = utc_now()
        with self._accounts.transaction():
            account = self._get_owned_account(session, transaction.target_account_number)
            updated = replace(account, balance=add_money(account.balance, transaction.amount))
            return self._accounts.save(updated)

    def withdraw(self, session: UserSession, transaction: Transaction) -> Account:
        validate_transaction(transaction, TransactionType.WITHDRAWAL)
        transaction.transaction_date = utc_now()
        with self._accounts.transaction():
            account = self._get_owned_account(session, transaction.target_account_number)
            require_funds(account, transaction.amount)
            updated = replace(account, balance=add_money(account.balance, -transaction.amount))
            return self._accounts.save(updated)

    def transfer(self, session: UserSession, transaction: Transaction) -> TransferResult:
        validate_transaction(transaction, TransactionType.TRANSFER)
        transaction.transaction_date = utc_now()
        with self._accounts.transaction():
            source = self._get_owned_account(session, transaction.source_account_number)
            target = self._get_account(transaction.target_account_number)
            require_funds(source, transaction.amount)
            source = replace(source, balance=add_money(source.balance, -transaction.amount))
            target = replace(target, balance=add_money(target.balance, transaction.amount))
            self._accounts.transfer_balance(source, target)
            return TransferResult(source, target)

    def _get_account(self, account_number: str) -> Account:
        if not is_valid_number(account_number):
            raise InvalidArgument("Account number must be valid")
        account = self._accounts.get_account(account_number)
        if account is None:
            raise NotFound("Account not found")
        if account.closed:
            raise Conflict("Account is closed")
        return account

    def _get_owned_account(self, session: UserSession, account_number: str) -> Account:
        account = self._get_account(account_number)
        if session is None or session.customer_number != account.customer_number:
            raise AccessDenied()
        return account
