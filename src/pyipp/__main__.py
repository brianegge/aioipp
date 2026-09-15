"""Command line diagnostics for the IPP client.

Run ``python -m pyipp ipp://printer.local:631/ipp/print`` to query a printer,
print what the library understands about it and save the raw IPP response to
a file that can be attached to a bug report.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from pathlib import Path
from typing import Any

from yarl import URL

from .const import DEFAULT_PRINTER_ATTRIBUTES
from .enums import IppOperation
from .exceptions import IPPError
from .ipp import IPP, VERSION
from .models import Printer
from .parser import parse

EXIT_OK = 0
EXIT_PARSE_FAILED = 1
EXIT_CONNECT_FAILED = 2

ISSUES_URL = "https://github.com/brianegge/aioipp/issues/new?template=bug_report.yml"


def _parse_version(value: str) -> tuple[int, int]:
    try:
        major, minor = (int(part) for part in value.split(".", 1))
    except ValueError as exc:
        msg = f"invalid IPP version {value!r}, expected MAJOR.MINOR"
        raise argparse.ArgumentTypeError(msg) from exc
    return (major, minor)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pyipp",
        description=(
            "Query an IPP printer, show what aioipp understands about it and "
            "save the raw response for bug reports."
        ),
    )
    parser.add_argument(
        "uri",
        help="printer URI, e.g. ipp://192.168.1.10:631/ipp/print",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="where to write the raw IPP response (default: ipp-<host>.bin)",
    )
    parser.add_argument(
        "--ipp-version",
        default="2.0",
        type=_parse_version,
        metavar="MAJOR.MINOR",
        help="IPP protocol version to request (default: 2.0, try 1.1 for old devices)",
    )
    parser.add_argument("--username", help="HTTP basic auth username")
    parser.add_argument("--password", help="HTTP basic auth password")
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="verify the printer's TLS certificate (ipps:// only)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=8,
        help="request timeout in seconds (default: 8)",
    )
    return parser


def _default_output(uri: str) -> Path:
    host = URL(uri).host or "printer"
    return Path(f"ipp-{host}.bin")


def _print_attributes(attributes: dict[str, Any]) -> None:
    for key in sorted(attributes):
        print(f"  {key}: {attributes[key]!r}")


async def _run(args: argparse.Namespace) -> int:
    output: Path = args.output or _default_output(args.uri)

    print(f"aioipp {VERSION}")
    print(f"Querying {args.uri} (IPP {'.'.join(map(str, args.ipp_version))})")

    async with IPP(
        args.uri,
        username=args.username,
        password=args.password,
        verify_ssl=args.verify_ssl,
        request_timeout=args.timeout,
        ipp_version=args.ipp_version,
    ) as ipp:
        try:
            raw = await ipp.raw(
                IppOperation.GET_PRINTER_ATTRIBUTES,
                {
                    "operation-attributes-tag": {
                        "requested-attributes": DEFAULT_PRINTER_ATTRIBUTES,
                    },
                },
            )
        except IPPError as exc:
            print(f"\nCould not talk to the printer: {exc}", file=sys.stderr)
            print(
                "Check the URI, try --ipp-version 1.1, or use ipps:// if the"
                " printer requires TLS.",
                file=sys.stderr,
            )
            return EXIT_CONNECT_FAILED

    await asyncio.to_thread(output.write_bytes, raw)
    print(f"Saved raw response ({len(raw)} bytes) to {output}")

    try:
        parsed = parse(raw)
        print(f"\nStatus code: {parsed['status-code']!r}")

        printers = parsed.get("printers") or []
        print(f"Printer attribute groups: {len(printers)}")

        if printers:
            print("\nRaw printer attributes:")
            _print_attributes(printers[0])

        print("\nParsed printer:")
        print(f"  {Printer.from_dict(printers[0] if printers else {})!r}")
    except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        print("\naioipp failed to parse this printer's response:\n", file=sys.stderr)
        traceback.print_exc()
        print(
            f"\nPlease open an issue at {ISSUES_URL} and attach {output}"
            " together with the output above.",
            file=sys.stderr,
        )
        print(
            "Note: the capture may contain the printer's serial number and"
            " UUID. Remove them from the issue if you consider them private.",
            file=sys.stderr,
        )
        return EXIT_PARSE_FAILED

    print(
        f"\nEverything parsed. If something still looks wrong, attach {output}"
        f" to an issue at {ISSUES_URL}.",
    )
    print(
        "Note: the capture may contain the printer's serial number and UUID.",
    )
    return EXIT_OK


async def run(argv: list[str] | None = None) -> int:
    """Run the diagnostics command and return an exit code."""
    return await _run(_build_parser().parse_args(argv))


def main(argv: list[str] | None = None) -> int:
    """Run the diagnostics command from a synchronous context."""
    return asyncio.run(run(argv))


if __name__ == "__main__":
    sys.exit(main())
