from fastapi import APIRouter, Response

from banking.api.dependencies import Access, Session
from banking.api.errors import PROBLEM_RESPONSES
from banking.api.schemas import CustomerDto, CustomerLoginRequest, CustomerLoginResponse
from banking.api.serialization import DecimalRoute, respond

router = APIRouter(
    prefix="/api/access", tags=["Access"], route_class=DecimalRoute, responses=PROBLEM_RESPONSES
)


@router.post("/login", response_model=CustomerLoginResponse)
def login(request: CustomerLoginRequest, access: Access) -> Response:
    session = access.login(request.identifier, request.pin)
    return respond(
        CustomerLoginResponse(
            customer=CustomerDto.model_validate(session.customer),
            sessionToken=session.session_token,
        )
    )


@router.post("/logout", status_code=204)
def logout(session: Session, access: Access) -> Response:
    access.logout(session)
    return Response(status_code=204)
