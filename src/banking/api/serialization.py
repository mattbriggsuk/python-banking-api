"""Preserve Java's numeric JSON money contract without converting Decimal to float."""

import json
from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import simplejson
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse

from banking.api.schemas import ApiModel


class DecimalRequest(Request):
    async def json(self) -> Any:
        if not hasattr(self, "_json"):
            self._json = json.loads(await self.body(), parse_float=Decimal)
        return self._json


class DecimalRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            return await handler(DecimalRequest(request.scope, request.receive))

        return handle


class DecimalJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return simplejson.dumps(
            content, use_decimal=True, allow_nan=False, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")


def respond(model: ApiModel, status_code: int = 200) -> Response:
    # DTO construction validates responses. Python mode avoids Decimal-to-string conversion.
    return DecimalJSONResponse(
        model.model_dump(mode="python", by_alias=True), status_code=status_code
    )
