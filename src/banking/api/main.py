from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from banking.api.errors import problem, register_error_handlers
from banking.api.routes import access, account, customer
from banking.bootstrap import Services, build_services
from banking.domain.exceptions import AuthenticationError


def create_app(services: Services | None = None) -> FastAPI:
    """Create an isolated application; callers may supply alternative service adapters."""
    app = FastAPI(title="Banking API", version="0.1.0")
    app.state.services = services if services is not None else build_services()
    register_error_handlers(app)

    @app.middleware("http")
    async def authenticate_and_prevent_caching(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.user_session = None
        authorization = request.headers.get("Authorization")
        if authorization is not None:
            try:
                # As in Java, an invalid supplied header also rejects public endpoints.
                request.state.user_session = await run_in_threadpool(
                    app.state.services.access.authenticated_session, authorization
                )
            except AuthenticationError as exception:
                return problem(request, 401, str(exception))
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(access.router)
    app.include_router(customer.router)
    app.include_router(account.router)

    # Runtime validation intentionally uses Java's 400 contract, not FastAPI's default 422.
    original_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        schema = original_openapi()
        for path in schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict) and "responses" in operation:
                    operation["responses"].pop("422", None)
        return schema

    app.openapi = openapi
    return app


app = create_app()
