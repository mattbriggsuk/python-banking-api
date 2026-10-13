from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from banking.domain.enums import AccountType, TransactionType


@dataclass(frozen=True, slots=True)
class Customer:
    customer_number: str | None
    first_name: str
    last_name: str
    email: str


@dataclass(frozen=True, slots=True)
class Account:
    account_number: str
    customer_number: str
    balance: Decimal = Decimal("0.00")
    closed: bool = False
    account_type: AccountType = AccountType.CURRENT


@dataclass(slots=True)
class Transaction:
    transaction_type: TransactionType
    amount: Decimal
    target_account_number: str
    source_account_number: str | None = None
    transaction_date: datetime | None = None


@dataclass(frozen=True, slots=True)
class CustomerRegistration:
    customer: Customer
    pin: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class UserSession:
    customer: Customer
    session_token: str = field(repr=False)

    @property
    def customer_number(self) -> str:
        assert self.customer.customer_number is not None
        return self.customer.customer_number


@dataclass(frozen=True, slots=True)
class StoredSession:
    customer_number: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TransferResult:
    from_account: Account
    to_account: Account
