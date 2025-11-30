from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from unpoly import Unpoly
from unpoly.adapter import BaseAdapter

if TYPE_CHECKING:  # pragma: no cover
    from starlette.requests import Request


UP_METHOD_COOKIE = "_up_method"


class UnpolyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.up = up = Unpoly(StarletteAdapter(request))
        response = await call_next(request)
        up.finalize_response(response)
        return response


class StarletteAdapter(BaseAdapter):
    def __init__(self, request: Request):
        self.request = request

    def request_headers(self) -> Mapping[str, str]:
        return dict(self.request.headers)

    def request_params(self) -> Mapping[str, str]:
        return dict(self.request.query_params)

    def redirect_uri(self, response: Response) -> str | None:
        return (
            response.headers.get("location")
            if 300 <= response.status_code < 400
            else None
        )

    def set_redirect_uri(self, response: Response, uri: str) -> None:
        response.headers["location"] = uri

    def set_headers(self, response: Response, headers: Mapping[str, str]) -> None:
        for k, v in headers.items():
            response.headers[k] = v

    def set_cookie(self, response: Response, needs_cookie: bool = False) -> None:
        if needs_cookie:
            response.set_cookie(
                key=UP_METHOD_COOKIE,
                value=self.method,
                httponly=True,  # Good security practice
                samesite="lax",  # CSRF protection
            )
        elif UP_METHOD_COOKIE in self.request.cookies:
            response.delete_cookie(UP_METHOD_COOKIE)

    @property
    def method(self) -> str:
        return self.request.method

    @property
    def location(self) -> str:
        # Reconstruct the full path with query string
        path = self.request.url.path
        if self.request.url.query:
            path += f"?{self.request.url.query}"
        return path
