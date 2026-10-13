from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from banking.bootstrap import Services
from banking.domain.exceptions import AuthenticationError
from banking.domain.models import UserSession
from banking.domain.services import AccessService, AccountService, CustomerService

bearer = HTTPBearer(auto_error=False, description="Opaque session token from registration or login")


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_access_service(services: Annotated[Services, Depends(get_services)]) -> AccessService:
    return services.access


def get_account_service(services: Annotated[Services, Depends(get_services)]) -> AccountService:
    return services.accounts


def get_customer_service(services: Annotated[Services, Depends(get_services)]) -> CustomerService:
    return services.customers


def require_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
) -> UserSession:
    if request.state.user_session is None:
        raise AuthenticationError("Log in to continue.")
    return request.state.user_session


Access = Annotated[AccessService, Depends(get_access_service)]
Accounts = Annotated[AccountService, Depends(get_account_service)]
Customers = Annotated[CustomerService, Depends(get_customer_service)]
Session = Annotated[UserSession, Depends(require_session)]
