from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, WithJsonSchema, field_validator
from pydantic.alias_generators import to_camel

from banking.domain.enums import AccountType, TransactionType
from banking.domain.models import Customer, Transaction

Number = Annotated[str, Field(strict=True, pattern=r"^[0-9]{16}$")]
Money = Annotated[Decimal, WithJsonSchema({"type": "number"}, mode="serialization")]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, from_attributes=True, extra="ignore"
    )


class CustomerInput(ApiModel):
    customer_number: str | None = None
    first_name: str = Field(strict=True, min_length=1)
    last_name: str = Field(strict=True, min_length=1)
    email: EmailStr

    @field_validator("first_name", "last_name")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value

    def to_domain(self) -> Customer:
        return Customer(self.customer_number, self.first_name, self.last_name, str(self.email))


class CustomerRegisterRequest(ApiModel):
    customer: CustomerInput


class CustomerLoginRequest(ApiModel):
    identifier: str = Field(strict=True, min_length=1, max_length=254)
    pin: str = Field(strict=True, pattern=r"^[0-9]{6}$", repr=False)

    @field_validator("identifier")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value


class AccountCreateRequest(ApiModel):
    account_type: AccountType = AccountType.CURRENT


class AccountCloseRequest(ApiModel):
    account_number: Number


class TransactionInput(ApiModel):
    transaction_type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
    target_account_number: Number
    source_account_number: Number | None = None
    transaction_date: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def reject_boolean_amount(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Amount must be a number")
        return value

    def to_domain(self) -> Transaction:
        return Transaction(
            self.transaction_type,
            self.amount,
            self.target_account_number,
            self.source_account_number,
            self.transaction_date,
        )


class AccountAmountRequest(ApiModel):
    transaction: TransactionInput


class CustomerDto(ApiModel):
    customer_number: str
    first_name: str
    last_name: str
    email: str


class AccountDto(ApiModel):
    account_number: str
    customer_number: str
    balance: Money
    closed: bool
    account_type: AccountType


class CustomerResponse(ApiModel):
    customer: CustomerDto


class CustomerLoginResponse(CustomerResponse):
    session_token: str = Field(repr=False)


class CustomerRegisterResponse(CustomerLoginResponse):
    pin: str = Field(repr=False)


class CustomerAccountResponse(ApiModel):
    customer_number: str
    accounts: list[AccountDto]


class AccountResponse(ApiModel):
    account: AccountDto


class AccountTransferResponse(ApiModel):
    from_account: AccountDto
    to_account: AccountDto


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
