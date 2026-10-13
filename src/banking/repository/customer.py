from threading import RLock

from banking.domain.exceptions import Conflict, InvalidArgument
from banking.domain.models import Customer


class InMemoryCustomerRepository:
    def __init__(self) -> None:
        self._customers: dict[str, tuple[Customer, str]] = {}
        self._emails: dict[str, str] = {}
        self._lock = RLock()

    def get_customer(self, customer_number: str) -> Customer | None:
        with self._lock:
            stored = self._customers.get(customer_number)
            return stored[0] if stored else None

    def get_customer_by_email(self, email: str) -> Customer | None:
        with self._lock:
            number = self._emails.get(email.strip().lower())
            return self.get_customer(number) if number else None

    def get_pin_hash(self, customer_number: str) -> str | None:
        with self._lock:
            stored = self._customers.get(customer_number)
            return stored[1] if stored else None

    def save(self, customer: Customer, pin_hash: str) -> Customer:
        with self._lock:
            number = customer.customer_number
            if number is None:
                raise InvalidArgument("Customer number is required")
            email = customer.email.strip().lower()
            if email in self._emails:
                raise Conflict("A customer with this email already exists. Log in instead.")
            if number in self._customers:
                raise Conflict("Customer number already exists")
            self._customers[number] = (customer, pin_hash)
            self._emails[email] = number
            return customer
