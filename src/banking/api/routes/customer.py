from typing import Annotated

from fastapi import APIRouter, Query, Response

from banking.api.dependencies import Access, Customers, Session
from banking.api.errors import PROBLEM_RESPONSES
from banking.api.schemas import (
    AccountDto,
    CustomerAccountResponse,
    CustomerDto,
    CustomerRegisterRequest,
    CustomerRegisterResponse,
    CustomerResponse,
)
from banking.api.serialization import DecimalRoute, respond

router = APIRouter(
    prefix="/api/customer",
    tags=["Customers"],
    route_class=DecimalRoute,
    responses=PROBLEM_RESPONSES,
)
CustomerNumber = Annotated[str, Query(alias="customerNumber")]


@router.post("/register", status_code=201, response_model=CustomerRegisterResponse)
def register(request: CustomerRegisterRequest, customers: Customers, access: Access) -> Response:
    registration = customers.register(request.customer.to_domain())
    token = access.start_session(registration.customer.customer_number)
    return respond(
        CustomerRegisterResponse(
            customer=CustomerDto.model_validate(registration.customer),
            pin=registration.pin,
            sessionToken=token,
        ),
        status_code=201,
    )


@router.get("/get", response_model=CustomerResponse)
def get_customer(
    customer_number: CustomerNumber, session: Session, customers: Customers
) -> Response:
    customer = customers.get_customer(session, customer_number)
    return respond(CustomerResponse(customer=CustomerDto.model_validate(customer)))


@router.get("/accounts", response_model=CustomerAccountResponse)
def get_accounts(
    customer_number: CustomerNumber, session: Session, customers: Customers
) -> Response:
    accounts = customers.get_customer_accounts(session, customer_number)
    return respond(
        CustomerAccountResponse(
            customerNumber=customer_number,
            accounts=[AccountDto.model_validate(account) for account in accounts],
        )
    )
