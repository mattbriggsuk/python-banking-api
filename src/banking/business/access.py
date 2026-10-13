import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta

from banking.domain.exceptions import AuthenticationError
from banking.domain.models import StoredSession, UserSession
from banking.domain.repositories import CustomerRepository, SessionRepository
from banking.utils.clock import utc_now
from banking.utils.pins import generate_pin, hash_pin, matches_pin


class AccessServiceImpl:
    def __init__(
        self,
        customers: CustomerRepository,
        sessions: SessionRepository,
        *,
        clock: Callable[[], datetime] = utc_now,
        session_lifetime: timedelta = timedelta(minutes=30),
    ) -> None:
        self._customers = customers
        self._sessions = sessions
        self._clock = clock
        self._session_lifetime = session_lifetime
        self._dummy_hash = hash_pin(generate_pin())

    def login(self, identifier: str, pin: str) -> UserSession:
        normalised = identifier.strip().lower()
        customer = (
            self._customers.get_customer_by_email(normalised)
            if "@" in normalised
            else self._customers.get_customer(normalised)
        )
        stored_hash = self._customers.get_pin_hash(customer.customer_number) if customer else None
        # Unknown customers still incur the same expensive hash derivation.
        matches = matches_pin(pin, stored_hash or self._dummy_hash)
        if (
            customer is None
            or stored_hash is None
            or re.fullmatch(r"[0-9]{6}", pin) is None
            or not matches
        ):
            raise AuthenticationError("Customer details or PIN are incorrect.")
        return UserSession(customer, self.start_session(customer.customer_number))

    def start_session(self, customer_number: str) -> str:
        now = self._clock()
        self._sessions.delete_expired(now)
        token = secrets.token_urlsafe(32)
        self._sessions.save(token, StoredSession(customer_number, now + self._session_lifetime))
        return token

    def authenticated_session(self, authorization: str | None) -> UserSession:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) <= 7:
            raise AuthenticationError("Log in to continue.")
        token = authorization[7:]
        stored = self._sessions.get(token)
        if stored is None or stored.expires_at <= self._clock():
            self._sessions.delete(token)
            raise AuthenticationError("Your session has expired. Log in again.")
        customer = self._customers.get_customer(stored.customer_number)
        if customer is None:
            raise AuthenticationError("Your session has expired. Log in again.")
        return UserSession(customer, token)

    def logout(self, session: UserSession) -> None:
        self._sessions.delete(session.session_token)
