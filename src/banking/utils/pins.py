import base64
import binascii
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def generate_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _derive(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, ITERATIONS, dklen=32)


def hash_pin(pin: str) -> str:
    """Use the same salt:hash base64 format and PBKDF2 parameters as Java."""
    salt = secrets.token_bytes(16)
    return ":".join(base64.b64encode(part).decode("ascii") for part in (salt, _derive(pin, salt)))


def matches_pin(pin: str, encoded: str) -> bool:
    try:
        salt_text, hash_text = encoded.split(":")
        salt = base64.b64decode(salt_text, validate=True)
        expected = base64.b64decode(hash_text, validate=True)
        if len(salt) != 16 or len(expected) != 32:
            return False
        return hmac.compare_digest(expected, _derive(pin, salt))
    except (ValueError, binascii.Error):
        return False
