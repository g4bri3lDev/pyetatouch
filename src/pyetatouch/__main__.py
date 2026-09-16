"""Command-line interface: python -m pyetatouch."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import aiohttp

from .client import DEFAULT_PORT, EtaClient
from .discovery import discover
from .dump import describe
from .exceptions import EtaError
from .models import VarAddress, decode_value


def _format(value: float | str | None, unit: str) -> str:
    if value is None:
        return "unavailable"
    return f"{value} {unit}".strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyetatouch")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("discover", help="list known components and variables").add_argument("host")
    read = commands.add_parser("read", help="read one variable")
    read.add_argument("host")
    read.add_argument("address")
    write = commands.add_parser("write", help="write one variable")
    write.add_argument("host")
    write.add_argument("address")
    write.add_argument("value", help="number, option label or option code")
    write.add_argument("--yes", action="store_true", help="actually send the write")
    dump = commands.add_parser("dump", help="write an anonymised structure report (no values)")
    dump.add_argument("host")
    dump.add_argument("-o", "--output", type=Path, help="file to write (default: stdout)")
    dump.add_argument("--no-info", action="store_true", help="skip varinfo (fast, less detail)")
    dump.add_argument("--keep-names", action="store_true", help="keep panel names")
    return parser


async def _discover(client: EtaClient) -> int:
    version = await client.check_api()
    installation = await discover(client)
    print(f"ETAtouch API {version} at {client.host}:{client.port}")
    for component in installation.components:
        kind = component.type or "unknown"
        title = component.name or kind
        print(f"\n{title} [{kind}] {component.node}/{component.fub}")
        for variable in installation.variables_for(component):
            print(f"  {variable.key:36} {variable.address}")
    print(f"\nvariables not in the catalog: {len(installation.unknown_variables)}")
    return 0


async def _dump(client: EtaClient, args: argparse.Namespace) -> int:
    def progress(done: int, total: int) -> None:
        print(f"\rvarinfo {done}/{total}", end="" if done < total else "\n", file=sys.stderr)

    report = await describe(
        client, with_info=not args.no_info, keep_names=args.keep_names, progress=progress
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is None:
        print(text)
    else:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    return 0


async def _read(client: EtaClient, address: VarAddress) -> int:
    value = await client.read(address)
    info = await client.var_info(address)
    print(f"{info.name}: {_format(decode_value(value, info), value.unit)} (raw {value.raw:g})")
    return 0


async def _write(client: EtaClient, address: VarAddress, text: str, confirmed: bool) -> int:
    info = await client.var_info(address)
    current = await client.read(address)
    target: float | str
    if not info.options:
        target = float(text)
    elif text.isdigit():
        target = int(text)
    else:
        target = text
    print(f"{info.name}: {_format(decode_value(current, info), current.unit)} -> {target}")
    if not confirmed:
        print("Refusing to write without --yes")
        return 2
    await client.write(address, target)
    updated = await client.read(address)
    print(f"now: {_format(decode_value(updated, info), updated.unit)}")
    return 0


async def async_main(argv: list[str] | None = None) -> int:
    """Run the CLI inside an existing event loop."""
    args = _parser().parse_args(argv)
    try:
        async with aiohttp.ClientSession() as session:
            client = EtaClient(session, args.host, args.port)
            if args.command == "discover":
                return await _discover(client)
            if args.command == "dump":
                return await _dump(client, args)
            address = VarAddress.parse(args.address)
            if args.command == "read":
                return await _read(client, address)
            return await _write(client, address, args.value, args.yes)
    except EtaError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    sys.exit(main())
