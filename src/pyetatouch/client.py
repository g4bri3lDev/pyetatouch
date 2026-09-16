"""Async client for the ETAtouch REST web service."""

from __future__ import annotations

import asyncio
import errno
import xml.etree.ElementTree as ET

import aiohttp

from .exceptions import (
    EtaConnectionError,
    EtaUnsupportedApiError,
    EtaWebserviceUnavailableError,
)
from .models import EtaFault, MenuFub, VarAddress, VarInfo, VarValue, encode_value
from .parsing import (
    parse_api_version,
    parse_document,
    parse_errors,
    parse_menu,
    parse_success,
    parse_value,
    parse_varinfo,
    parse_varset,
)

DEFAULT_PORT = 8080
MIN_API_VERSION = (1, 2)


def _is_refused(error: aiohttp.ClientConnectorError) -> bool:
    os_error = error.os_error
    return isinstance(os_error, ConnectionRefusedError) or os_error.errno == errno.ECONNREFUSED


class EtaClient:
    """Client for one ETAtouch controller."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = DEFAULT_PORT,
        *,
        timeout: float = 10.0,
        max_parallel: int = 3,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._info_cache: dict[VarAddress, VarInfo] = {}

    async def _request(
        self, method: str, path: str, data: dict[str, str] | None = None
    ) -> ET.Element:
        url = f"{self._base_url}{path}"
        async with self._semaphore:
            try:
                async with self._session.request(
                    method, url, data=data, timeout=self._timeout
                ) as response:
                    body = await response.read()
                    status = response.status
            except aiohttp.ClientConnectorError as err:
                if _is_refused(err):
                    raise EtaWebserviceUnavailableError(
                        f"{self._base_url} refused the connection"
                    ) from err
                raise EtaConnectionError(f"Cannot connect to {self._base_url}: {err}") from err
            except (aiohttp.ClientError, TimeoutError) as err:
                raise EtaConnectionError(f"{method} {url} failed: {err!r}") from err
        return parse_document(body, status)

    async def api_version(self) -> str:
        """Return the web service API version."""
        return parse_api_version(await self._request("GET", "/user/api"))

    async def check_api(self) -> str:
        """Return the API version, raising if it is older than 1.2."""
        version = await self.api_version()
        try:
            parsed = tuple(int(part) for part in version.split("."))
        except ValueError as err:
            raise EtaUnsupportedApiError(version) from err
        if parsed < MIN_API_VERSION:
            raise EtaUnsupportedApiError(version)
        return version

    async def menu(self) -> list[MenuFub]:
        """Return the top-level function blocks and their variables."""
        return parse_menu(await self._request("GET", "/user/menu"))

    async def read(self, address: VarAddress) -> VarValue:
        """Read a single variable."""
        return parse_value(await self._request("GET", f"/user/var/{address}"))

    async def var_info(self, address: VarAddress, *, refresh: bool = False) -> VarInfo:
        """Return (cached) metadata of a variable."""
        if refresh or address not in self._info_cache:
            root = await self._request("GET", f"/user/varinfo/{address}")
            self._info_cache[address] = parse_varinfo(root)
        return self._info_cache[address]

    async def write_raw(self, address: VarAddress, raw: int) -> None:
        """Write a raw (unscaled) value without client-side validation."""
        root = await self._request("POST", f"/user/var/{address}", data={"value": str(raw)})
        parse_success(root)

    async def write(self, address: VarAddress, value: float | str) -> None:
        """Validate and write a user-facing value (number or option label/code)."""
        info = await self.var_info(address)
        await self.write_raw(address, encode_value(info, value))

    async def errors(self) -> list[EtaFault]:
        """Return all active faults."""
        return parse_errors(await self._request("GET", "/user/errors"))

    async def create_varset(self, name: str) -> None:
        """Create an empty variable set."""
        parse_success(await self._request("PUT", f"/user/vars/{name}"))

    async def delete_varset(self, name: str) -> None:
        """Delete a variable set."""
        parse_success(await self._request("DELETE", f"/user/vars/{name}"))

    async def add_to_varset(self, name: str, address: VarAddress) -> None:
        """Add a variable to a variable set."""
        parse_success(await self._request("PUT", f"/user/vars/{name}/{address}"))

    async def read_varset(self, name: str) -> dict[VarAddress, VarValue]:
        """Read all variables of a variable set."""
        return parse_varset(await self._request("GET", f"/user/vars/{name}"))
