from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from banking.api.schemas import ProblemDetail
from banking.domain.exceptions import (
    AccessDenied,
    AuthenticationError,
    BankingError,
    Conflict,
    InvalidArgument,
    NotFound,
)

ERROR_STATUSES: dict[type[BankingError], int] = {
    InvalidArgument: 400,
    AuthenticationError: 401,
    AccessDenied: 403,
    NotFound: 404,
    Conflict: 409,
}
PROBLEM_RESPONSES = {
    code: {"model": ProblemDetail, "description": HTTPStatus(code).phrase}
    for code in (400, 401, 403, 404, 409)
}


def problem(request: Request, status: int, detail: str) -> JSONResponse:
    body = ProblemDetail(
        title=HTTPStatus(status).phrase, status=status, detail=detail, instance=request.url.path
    )
    headers = {"Cache-Control": "no-store"}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        body.model_dump(),
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BankingError)
    async def banking_error(request: Request, exception: BankingError) -> JSONResponse:
        return problem(request, ERROR_STATUSES.get(type(exception), 500), str(exception))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exception: RequestValidationError) -> JSONResponse:
        # Do not echo rejected input, which may contain PINs or session tokens.
        return problem(request, 400, "Please check required fields and their formats.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exception: HTTPException) -> JSONResponse:
        return problem(request, exception.status_code, str(exception.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exception: Exception) -> JSONResponse:
        return problem(request, 500, "An unexpected error occurred.")
