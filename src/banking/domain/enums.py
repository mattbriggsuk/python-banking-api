from enum import StrEnum


class AccountType(StrEnum):
    CURRENT = "CURRENT"
    SAVINGS = "SAVINGS"
    CREDIT = "CREDIT"


class TransactionType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
