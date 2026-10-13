import re
import secrets


def _luhn_sum(value: str) -> int:
    total = 0
    for index, character in enumerate(value):
        digit = int(character)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total


def generate_number() -> str:
    """Generate 15 random digits followed by a Luhn check digit."""
    digits = str(secrets.randbelow(9) + 1) + "".join(str(secrets.randbelow(10)) for _ in range(14))
    return digits + str(-_luhn_sum(digits) % 10)


def is_valid_number(value: str | None) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]{16}", value) is not None
        and _luhn_sum(value) % 10 == 0
    )
