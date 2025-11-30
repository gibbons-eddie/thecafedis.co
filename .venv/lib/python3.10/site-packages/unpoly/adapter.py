"""
Adapters
========

This library uses adapters to implement the "I/O parts", namely reading and writing
headers from HTTP requests and response. To adapt this library to a new framework it is
neccessary to subclass :class:`.BaseAdapter` and then initialize
:class:`unpoly.up.Unpoly` with it. Since :class:`unpoly.up.Unpoly` is initialized once
per request, it makes sense to pass the request to the adapter via init, but there is
no requirement for this -- the adapter could simply access the request via
thread-locals or other means.

As an example the usage with the builtin Django Adapter looks like this:

.. code-block:: python

    from unpoly import Unpoly
    from unpoly.contrib.django import DjangoAdapter
    # The following code is run in a middleware, once per request
    adapter = DjangoAdapter(request)
    # Attach `Unpoly` to the request, so views can easily acces it
    request.up = Unpoly(adapter)
    # Actually execute the view and get the response object
    response = handle_view(request)
    # Tell `Unpoly` to set the relevant `X-Up-*` headers
    request.up.finalize_response(response)

"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping


class BaseAdapter:
    """
    Provides the entrypoint for other frameworks to use this library.

    Implements common functionality that is not often overriden as well
    as framework specific hooks.
    """

    def request_headers(self) -> Mapping[str, str]:
        """Reads the request headers from the current request.

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def request_params(self) -> Mapping[str, str]:
        """Reads the GET params from the current request.

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def redirect_uri(self, response: Any) -> str | None:
        """Returns the redirect target of a response or None if the response
        is not a redirection (ie if it's status code is not in the range 300-400).

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def set_redirect_uri(self, response: Any, uri: str) -> None:
        """Set a new redirect target for the current response. This is used to
        pass unpoly parameters via GET params through redirects.

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def set_headers(self, response: Any, headers: Mapping[str, str]) -> None:
        """Set headers like `X-Up-Location` on the current response.

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def set_cookie(self, response: Any, needs_cookie: bool = False) -> None:
        """Set or delete the `_up_method <https://unpoly.com/_up_method>`_ cookie.

        The implementation should set the cookie if `needs_cookie` is `True` and
        otherwise remove it if set.

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    @property
    def method(self) -> str:
        """Exposes the current request's method (GET/POST etc)

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    @property
    def location(self) -> str:
        """Exposes the current request's location (path including query params)

        Needs to be implemented."""
        raise NotImplementedError  # pragma: no cover

    def deserialize_data(self, data: str) -> object:
        """Deserializes data passed in by Unpoly.

        By default it simply reads it as JSON, but can be overriden if custom
        decoders are needed.
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    def serialize_data(self, data: object) -> str:
        """Serializes the data for passing it to Unpoly.

        By default it simply serializes it as JSON, but can be overriden if custom
        encoders are needed.
        """
        return json.dumps(data, separators=(",", ":"), ensure_ascii=True)


class SimpleAdapter(BaseAdapter):
    def __init__(
        self,
        method: str = "GET",
        location: str = "/",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        redirect_uri: str | None = None,
    ):
        self._method = method
        self._location = location
        self.headers = headers or {}
        self.params = params or {}
        self._redirect_uri = redirect_uri
        self.response_redirect_uri: str | None = None
        self.response_headers: Mapping[str, str] | None = None
        self.cookie: bool | None = None

    def request_headers(self) -> Mapping[str, str]:
        return self.headers

    def request_params(self) -> Mapping[str, str]:
        return self.params

    def redirect_uri(self, response: object) -> str | None:
        return self._redirect_uri

    def set_redirect_uri(self, response: object, uri: str) -> None:
        self.response_redirect_uri = uri

    def set_headers(self, response: object, headers: Mapping[str, str]) -> None:
        self.response_headers = headers

    def set_cookie(self, response: object, needs_cookie: bool = False) -> None:
        self.cookie = needs_cookie

    @property
    def method(self) -> str:
        return self._method

    @property
    def location(self) -> str:
        return self._location
