from fastapi import APIRouter, Response

from banking.api.dependencies import Accounts, Session
from banking.api.errors import PROBLEM_RESPONSES
from banking.api.schemas import (
    AccountAmountRequest,
    AccountCloseRequest,
    AccountCreateRequest,
    AccountDto,
    AccountResponse,
    AccountTransferResponse,
)
from banking.api.serialization import DecimalRoute, respond

router = APIRouter(
    prefix="/api/account", tags=["Accounts"], route_class=DecimalRoute, responses=PROBLEM_RESPONSES
)


@router.post("/create", status_code=201, response_model=AccountResponse)
def create(request: AccountCreateRequest, session: Session, accounts: Accounts) -> Response:
    account = accounts.create(session, request.account_type)
    return respond(AccountResponse(account=AccountDto.model_validate(account)), status_code=201)


@router.post("/close", status_code=202, response_model=AccountResponse)
def close(request: AccountCloseRequest, session: Session, accounts: Accounts) -> Response:
    account = accounts.close(session, request.account_number)
    return respond(AccountResponse(account=AccountDto.model_validate(account)), status_code=202)


@router.post("/deposit", response_model=AccountResponse)
def deposit(request: AccountAmountRequest, session: Session, accounts: Accounts) -> Response:
    account = accounts.deposit(session, request.transaction.to_domain())
    return respond(AccountResponse(account=AccountDto.model_validate(account)))


@router.post("/withdraw", response_model=AccountResponse)
def withdraw(request: AccountAmountRequest, session: Session, accounts: Accounts) -> Response:
    account = accounts.withdraw(session, request.transaction.to_domain())
    return respond(AccountResponse(account=AccountDto.model_validate(account)))


@router.post("/transfer", response_model=AccountTransferResponse)
def transfer(request: AccountAmountRequest, session: Session, accounts: Accounts) -> Response:
    result = accounts.transfer(session, request.transaction.to_domain())
    return respond(
        AccountTransferResponse(
            fromAccount=AccountDto.model_validate(result.from_account),
            toAccount=AccountDto.model_validate(result.to_account),
        )
    )
