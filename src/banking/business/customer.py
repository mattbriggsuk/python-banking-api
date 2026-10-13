from banking.domain.exceptions import AccessDenied, Conflict, InvalidArgument, NotFound
from banking.domain.models import Account, Customer, CustomerRegistration, UserSession
from banking.domain.repositories import AccountRepository, CustomerRepository
from banking.utils.numbers import generate_number, is_valid_number
from banking.utils.pins import generate_pin, hash_pin


class CustomerServiceImpl:
    def __init__(self, customers: CustomerRepository, accounts: AccountRepository) -> None:
        self._customers = customers
        self._accounts = accounts

    def register(self, customer: Customer) -> CustomerRegistration:
        if customer is None or any(
            not isinstance(value, str) or not value.strip()
            for value in (customer.first_name, customer.last_name, customer.email)
        ):
            raise InvalidArgument("Customer and all required details must be provided")
        if self._customers.get_customer_by_email(customer.email) is not None:
            raise Conflict("A customer with this email already exists. Log in instead.")
        number = generate_number()
        while self._customers.get_customer(number) is not None:
            number = generate_number()
        pin = generate_pin()
        registered = Customer(
            number,
            customer.first_name.strip(),
            customer.last_name.strip(),
            customer.email.strip().lower(),
        )
        saved = self._customers.save(registered, hash_pin(pin))
        return CustomerRegistration(saved, pin)

    def get_customer(self, session: UserSession, customer_number: str) -> Customer:
        if not is_valid_number(customer_number):
            raise InvalidArgument("Customer number must be a valid 16-digit number")
        if session is None or session.customer_number != customer_number:
            raise AccessDenied()
        customer = self._customers.get_customer(customer_number)
        if customer is None:
            raise NotFound("Customer not found")
        return customer

    def get_customer_accounts(self, session: UserSession, customer_number: str) -> list[Account]:
        self.get_customer(session, customer_number)
        return self._accounts.get_customer_accounts(customer_number)
