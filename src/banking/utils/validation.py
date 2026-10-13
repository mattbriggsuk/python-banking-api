from decimal import Decimal, localcontext

from banking.domain.enums import TransactionType
from banking.domain.exceptions import Conflict, InvalidArgument
from banking.domain.models import Account, Transaction
from banking.utils.numbers import is_valid_number


def validate_transaction(transaction: Transaction, expected_type: TransactionType) -> None:
    if transaction is None:
        raise InvalidArgument("Transaction is required")
    if transaction.transaction_type != expected_type:
        raise InvalidArgument(f"Transaction type must be {expected_type}")
    amount = transaction.amount
    if (
        not isinstance(amount, Decimal)
        or not amount.is_finite()
        or amount <= 0
        or amount.as_tuple().exponent < -2
        or amount.adjusted() >= 16
    ):
        raise InvalidArgument(
            "Amount must be positive with at most two decimal places and 16 integer digits"
        )
    if not is_valid_number(transaction.target_account_number):
        raise InvalidArgument("Target account number must be valid")
    if expected_type == TransactionType.TRANSFER:
        if not is_valid_number(transaction.source_account_number):
            raise InvalidArgument("Source account number must be valid for transfers")
        if transaction.source_account_number == transaction.target_account_number:
            raise InvalidArgument("Source and target accounts must differ")
    elif transaction.source_account_number and transaction.source_account_number.strip():
        raise InvalidArgument("Source account number is only valid for transfers")


def require_funds(account: Account, amount: Decimal) -> None:
    if account.balance < amount:
        raise Conflict("Insufficient funds")


def add_money(balance: Decimal, amount: Decimal) -> Decimal:
    """Keep arithmetic exact even when a balance grows past Decimal's default precision."""
    with localcontext() as context:
        context.prec = max(28, balance.adjusted() + 4, amount.adjusted() + 4)
        return balance + amount
