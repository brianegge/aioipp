"""Tests for the scrubbed response carried by IPPParseError."""

from __future__ import annotations

import struct
import traceback
from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientSession
from aresponses import ResponsesMockServer

from pyipp import IPP, IPPParseError
from pyipp.__main__ import EXIT_OK, EXIT_PARSE_FAILED, run
from pyipp.const import DEFAULT_PRINTER_ATTRIBUTES
from pyipp.enums import IppOperation, IppTag
from pyipp.scrub import CAPTURE_BEGIN, decode_capture, encode_capture, scrub

from . import (
    DEFAULT_PRINTER_HOST,
    DEFAULT_PRINTER_PATH,
    DEFAULT_PRINTER_PORT,
    DEFAULT_PRINTER_URI,
    load_fixture_binary,
)

if TYPE_CHECKING:
    from pathlib import Path

MATCH_DEFAULT_HOST = f"{DEFAULT_PRINTER_HOST}:{DEFAULT_PRINTER_PORT}"
SERIAL = b"VND1B47698"


def _attr(tag: int, name: str, value: bytes) -> bytes:
    encoded = name.encode()
    return (
        struct.pack(">bh", tag, len(encoded))
        + encoded
        + struct.pack(">h", len(value))
        + value
    )


# Parses, but printer-state has two values, so building the Printer fails.
UNSUPPORTED_PRINTER = (
    struct.pack(">bbhi", 2, 0, 0, 1)
    + bytes([IppTag.OPERATION])
    + _attr(IppTag.CHARSET, "attributes-charset", b"utf-8")
    + bytes([IppTag.PRINTER])
    + _attr(
        IppTag.TEXT,
        "printer-device-id",
        b"MFG:HP;MDL:LaserJet;SN:" + SERIAL + b";",
    )
    + _attr(IppTag.ENUM, "printer-state", struct.pack(">i", 3))
    + _attr(IppTag.ENUM, "", struct.pack(">i", 3))
    + bytes([IppTag.END])
)


def _add_response(aresponses: ResponsesMockServer, body: bytes) -> None:
    aresponses.add(
        MATCH_DEFAULT_HOST,
        DEFAULT_PRINTER_PATH,
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/ipp"},
            body=body,
        ),
    )


def _logged(error: BaseException) -> str:
    """Return the traceback text a logger would write for error."""
    return "".join(traceback.format_exception(error))


@pytest.mark.asyncio
async def test_printer_parse_error_carries_scrubbed_response(
    aresponses: ResponsesMockServer,
) -> None:
    """A Printer that cannot be built reports the cause and the response."""
    _add_response(aresponses, UNSUPPORTED_PRINTER)

    async with ClientSession() as session:
        ipp = IPP(DEFAULT_PRINTER_URI, session=session)
        with pytest.raises(IPPParseError) as excinfo:
            await ipp.printer()

    error = excinfo.value
    assert str(error).startswith("TypeError: ")
    assert CAPTURE_BEGIN not in str(error)
    assert error.scrubbed_response == scrub(UNSUPPORTED_PRINTER)
    assert SERIAL not in error.scrubbed_response

    logged = _logged(error)
    assert CAPTURE_BEGIN in logged
    assert SERIAL.decode() not in logged
    assert decode_capture(logged) == error.scrubbed_response


@pytest.mark.asyncio
async def test_execute_parse_error_carries_scrubbed_response(
    aresponses: ResponsesMockServer,
) -> None:
    """A response that cannot be parsed at all is attached too."""
    body = load_fixture_binary("get-printer-attributes-epsonxp6000.bin")[:40]
    _add_response(aresponses, body)

    async with ClientSession() as session:
        ipp = IPP(DEFAULT_PRINTER_URI, session=session)
        with pytest.raises(IPPParseError) as excinfo:
            await ipp.execute(
                IppOperation.GET_PRINTER_ATTRIBUTES,
                {
                    "operation-attributes-tag": {
                        "requested-attributes": DEFAULT_PRINTER_ATTRIBUTES,
                    },
                },
            )

    assert str(excinfo.value).startswith("error: ")
    assert excinfo.value.scrubbed_response == scrub(body)
    assert decode_capture(_logged(excinfo.value)) == scrub(body)


def test_parse_error_without_response() -> None:
    """Errors raised without a response keep working as before."""
    error = IPPParseError("Invalid DATE size 12")

    assert str(error) == "Invalid DATE size 12"
    assert error.scrubbed_response is None


def test_capture_round_trip_through_pasting() -> None:
    """A block survives indentation, quoting and surrounding text."""
    data = load_fixture_binary("get-printer-attributes-kyocera-fs4100dn.bin")
    block = encode_capture(data)
    pasted = "Here is my log:\n" + "\n".join(
        f">   {line}" for line in block.split("\n")
    )

    assert all(len(line) <= 76 for line in block.split("\n")[1:-1])
    assert decode_capture(pasted) == data


def test_capture_missing() -> None:
    """Text without a block is rejected."""
    with pytest.raises(ValueError, match="no -----BEGIN"):
        decode_capture("Traceback (most recent call last):")


async def test_cli_from_log(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--from-log rebuilds the capture from a pasted log and parses it."""
    data = load_fixture_binary("get-printer-attributes-kyocera-fs4100dn.bin")
    log = tmp_path / "home-assistant.log"
    log.write_text(f"IPP Parse Error\n{encode_capture(data)}\n", encoding="utf-8")
    output = tmp_path / "capture.bin"

    assert await run(["--from-log", str(log), "-o", str(output)]) == EXIT_OK

    assert output.read_bytes() == data
    assert "printer-make-and-model: 'FS-4100DN'" in capsys.readouterr().out


async def test_cli_from_log_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--from-log - reads the log from stdin."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.stdin.read",
        lambda: encode_capture(UNSUPPORTED_PRINTER),
    )

    assert await run(["--from-log", "-"]) == EXIT_PARSE_FAILED
    assert (tmp_path / "ipp-from-log.bin").read_bytes() == scrub(UNSUPPORTED_PRINTER)


async def test_cli_from_log_without_block(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A file without a block is reported, not a traceback."""
    log = tmp_path / "home-assistant.log"
    log.write_text("nothing here\n", encoding="utf-8")

    assert await run(["--from-log", str(log)]) == EXIT_PARSE_FAILED
    assert "Could not read a response" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [[], [DEFAULT_PRINTER_URI, "--from-log", "home-assistant.log"]],
)
async def test_cli_needs_uri_or_log(argv: list[str]) -> None:
    """Exactly one of a URI and --from-log is required."""
    with pytest.raises(SystemExit):
        await run(argv)
