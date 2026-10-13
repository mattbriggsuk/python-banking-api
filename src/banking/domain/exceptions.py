"""Expected failures; HTTP status mapping belongs to the API layer."""


class BankingError(Exception):
    pass


class InvalidArgument(BankingError):
    pass


class AuthenticationError(BankingError):
    pass


class AccessDenied(BankingError):
    def __init__(self) -> None:
        super().__init__("You cannot access another customer's accounts")


class NotFound(BankingError):
    pass


class Conflict(BankingError):
    pass
