from decimal import Decimal

import pytest

from banking.domain.enums import TransactionType
from banking.domain.exceptions import InvalidArgument
from banking.domain.models import Transaction
from banking.utils.numbers import generate_number, is_valid_number
from banking.utils.pins import generate_pin, hash_pin, matches_pin
from banking.utils.validation import add_money, validate_transaction


def test_generated_numbers_and_checksum():
    numbers = {generate_number() for _ in range(100)}
    assert len(numbers) == 100
    for number in numbers:
        assert is_valid_number(number)
        assert number[0] != "0"
        corrupted = number[:-1] + str((int(number[-1]) + 1) % 10)
        assert not is_valid_number(corrupted)


@pytest.mark.parametrize(
    "value", [None, "", "123", "１２３４５６７８９０１２３４５６", "0000000000000001"]
)
def test_invalid_numbers(value):
    assert not is_valid_number(value)


def test_pin_salt_hash_and_leading_zeros():
    pin = "012345"
    first, second = hash_pin(pin), hash_pin(pin)
    assert first != second
    assert matches_pin(pin, first)
    assert not matches_pin("123456", first)
    assert not matches_pin(pin, "malformed")
    assert not matches_pin(pin, "!!!!:!!!!")
    assert len(generate_pin()) == 6


@pytest.mark.parametrize(
    "amount", ["0", "-1", "0.001", "1.000", "10000000000000000", "NaN", "Infinity"]
)
def test_business_amount_validation(amount):
    transaction = Transaction(TransactionType.DEPOSIT, Decimal(amount), generate_number())
    with pytest.raises(InvalidArgument):
        validate_transaction(transaction, TransactionType.DEPOSIT)


def test_arithmetic_exceeds_default_decimal_precision_without_rounding():
    assert add_money(Decimal("9999999999999999999999999999.99"), Decimal("0.01")) == Decimal(
        "10000000000000000000000000000.00"
    )
