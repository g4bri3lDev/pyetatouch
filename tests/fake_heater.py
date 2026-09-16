"""A fake ETAtouch web service served over real HTTP for tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from aiohttp import web
from aiohttp.test_utils import TestServer

from tests.helpers import NS_URI, load_fixture

XML = "text/xml"


def document(body: str) -> str:
    """Wrap a body in the heater's <eta> envelope."""
    return f'<?xml version="1.0" encoding="utf-8"?><eta version="1.0" xmlns="{NS_URI}">{body}</eta>'


@dataclass
class Value:
    """A variable value as the heater reports it."""

    raw: str
    text: str
    unit: str = ""
    scale: int = 1
    offset: int = 0

    def element(self, tag: str, uri: str) -> str:
        return (
            f'<{tag} advTextOffset="{self.offset}" unit="{self.unit}" uri="{uri}" '
            f'strValue="{self.text}" scaleFactor="{self.scale}" decPlaces="0">{self.raw}</{tag}>'
        )


@dataclass
class FakeHeater:
    """In-memory heater state; handlers read it on every request."""

    api: str = field(default_factory=lambda: load_fixture("api.xml"))
    menu: str = field(default_factory=lambda: load_fixture("menu_small.xml"))
    errors: str = field(default_factory=lambda: load_fixture("errors_none.xml"))
    values: dict[str, Value] = field(default_factory=dict)
    varinfo: dict[str, str] = field(default_factory=dict)
    varinfo_factory: Callable[[str], str] | None = None
    restricted: set[str] = field(default_factory=set)
    varsets: dict[str, list[str]] = field(default_factory=dict)
    write_errors: dict[str, tuple[int, str]] = field(default_factory=dict)
    writes: list[tuple[str, str]] = field(default_factory=list)
    requests: list[tuple[str, str]] = field(default_factory=list)
    responses: dict[tuple[str, str], tuple[int, str]] = field(default_factory=dict)
    delays: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def _ok(body: str, status: int = 200) -> web.Response:
        return web.Response(status=status, text=document(body), content_type=XML)

    @staticmethod
    def _error(status: int, uri: str, message: str) -> web.Response:
        return web.Response(
            status=status,
            text=document(f'<error uri="{uri}">{message}</error>'),
            content_type=XML,
        )

    @web.middleware
    async def _middleware(
        self,
        request: web.Request,
        handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
    ) -> web.StreamResponse:
        self.requests.append((request.method, request.path))
        if delay := self.delays.get(request.path):
            await asyncio.sleep(delay)
        override = self.responses.get((request.method, request.path))
        if override is not None:
            status, body = override
            return web.Response(status=status, text=body, content_type=XML)
        return await handler(request)

    def app(self) -> web.Application:
        app = web.Application(middlewares=[self._middleware])
        app.router.add_get("/user/api", self._get_api)
        app.router.add_get("/user/menu", self._get_menu)
        app.router.add_get("/user/errors", self._get_errors)
        app.router.add_get("/user/var/{address:.+}", self._get_var)
        app.router.add_post("/user/var/{address:.+}", self._post_var)
        app.router.add_get("/user/varinfo/{address:.+}", self._get_varinfo)
        app.router.add_put("/user/vars/{name}", self._put_set)
        app.router.add_get("/user/vars/{name}", self._get_set)
        app.router.add_delete("/user/vars/{name}", self._delete_set)
        app.router.add_put("/user/vars/{name}/{address:.+}", self._put_set_var)
        return app

    async def _get_api(self, request: web.Request) -> web.Response:
        return web.Response(text=self.api, content_type=XML)

    async def _get_menu(self, request: web.Request) -> web.Response:
        return web.Response(text=self.menu, content_type=XML)

    async def _get_errors(self, request: web.Request) -> web.Response:
        return web.Response(text=self.errors, content_type=XML)

    async def _get_var(self, request: web.Request) -> web.Response:
        address = request.match_info["address"]
        if address in self.restricted:
            return self._error(400, request.path, "Invalid permission")
        value = self.values.get(address)
        if value is None:
            return self._error(400, request.path, "Unknown variable")
        return self._ok(value.element("value", request.path))

    async def _post_var(self, request: web.Request) -> web.Response:
        address = request.match_info["address"]
        form = await request.post()
        self.writes.append((address, str(form.get("value"))))
        if address in self.write_errors:
            status, message = self.write_errors[address]
            return self._error(status, request.path, message)
        return self._ok(f'<success uri="{request.path}"/>')

    async def _get_varinfo(self, request: web.Request) -> web.Response:
        address = request.match_info["address"]
        if address in self.restricted:
            return self._error(400, request.path, "Invalid permission")
        body = self.varinfo.get(address)
        if body is None and self.varinfo_factory is not None:
            body = self.varinfo_factory(address)
        if body is None:
            return self._error(400, request.path, "Unknown variable")
        return web.Response(text=body, content_type=XML)

    async def _put_set(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        if name in self.varsets:
            return self._error(400, request.path, "Variable set already exists")
        self.varsets[name] = []
        return self._ok(f'<success uri="{request.path}"/>', status=201)

    async def _put_set_var(self, request: web.Request) -> web.Response:
        name, address = request.match_info["name"], request.match_info["address"]
        if name not in self.varsets:
            return self._error(404, request.path, "Variable set not available")
        if address in self.restricted:
            return self._error(400, request.path, "Invalid permission")
        if address in self.varsets[name]:
            return self._error(400, request.path, "Can not add the variable to the variable set")
        self.varsets[name].append(address)
        return self._ok(f'<success uri="{request.path}"/>', status=201)

    async def _get_set(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        if name not in self.varsets:
            return self._error(404, request.path, "Variable set not available")
        variables = "".join(
            self.values.get(address, Value("0", "0")).element("variable", address)
            for address in self.varsets[name]
        )
        return self._ok(f'<vars uri="{request.path}">{variables}</vars>')

    async def _delete_set(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        if self.varsets.pop(name, None) is None:
            return self._error(404, request.path, "Variable set not available")
        return self._ok(f'<success uri="{request.path}"/>')


@asynccontextmanager
async def serve(heater: FakeHeater) -> AsyncIterator[tuple[str, int]]:
    """Serve the fake heater on localhost and yield (host, port)."""
    server = TestServer(heater.app())
    await server.start_server()
    try:
        assert server.port is not None
        yield server.host, server.port
    finally:
        await server.close()
