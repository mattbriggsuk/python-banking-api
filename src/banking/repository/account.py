from collections.abc import Iterator
from contextlib import contextmanager
from threading import RLock

from banking.domain.models import Account


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._lock = RLock()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Hold the repository lock across a complete business operation."""
        with self._lock:
            yield

    def get_account(self, account_number: str) -> Account | None:
        with self._lock:
            return self._accounts.get(account_number)

    def get_customer_accounts(self, customer_number: str) -> list[Account]:
        with self._lock:
            return [a for a in self._accounts.values() if a.customer_number == customer_number]

    def save(self, account: Account) -> Account:
        with self._lock:
            self._accounts[account.account_number] = account
            return account

    def transfer_balance(self, from_account: Account, to_account: Account) -> None:
        with self._lock:
            self._accounts.update(
                {from_account.account_number: from_account, to_account.account_number: to_account}
            )
