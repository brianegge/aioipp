"""Tests for the command line diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aresponses import ResponsesMockServer

from pyipp.__main__ import (
    EXIT_CONNECT_FAILED,
    EXIT_OK,
    EXIT_PARSE_FAILED,
    _parse_version,
    main,
    run,
)

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


async def test_cli_success(
    aresponses: ResponsesMockServer,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the CLI prints the parsed printer and saves the capture."""
    body = load_fixture_binary("get-printer-attributes-epsonxp6000.bin")
    _add_response(aresponses, body)
    output = tmp_path / "capture.bin"

    assert await run([DEFAULT_PRINTER_URI, "--output", str(output)]) == EXIT_OK

    assert output.read_bytes() == body
    out = capsys.readouterr().out
    assert "printer-make-and-model: 'EPSON XP-6000 Series'" in out
    assert "Parsed printer:" in out
    assert "Everything parsed" in out


async def test_cli_parse_failure(
    aresponses: ResponsesMockServer,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the CLI still saves the capture and prints a traceback on failure."""
    body = load_fixture_binary("get-printer-attributes-epsonxp6000.bin")[:40]
    _add_response(aresponses, body)
    output = tmp_path / "capture.bin"

    assert await run([DEFAULT_PRINTER_URI, "-o", str(output)]) == EXIT_PARSE_FAILED

    assert output.read_bytes() == body
    captured = capsys.readouterr()
    assert "failed to parse" in captured.err
    assert "Traceback" in captured.err
    assert "attach" in captured.err


async def test_cli_connection_failure(
    aresponses: ResponsesMockServer,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the CLI reports connection problems without writing a capture."""
    aresponses.add(
        MATCH_DEFAULT_HOST,
        DEFAULT_PRINTER_PATH,
        "POST",
        aresponses.Response(status=500, body=b"boom"),
    )
    output = tmp_path / "capture.bin"

    assert await run([DEFAULT_PRINTER_URI, "-o", str(output)]) == EXIT_CONNECT_FAILED

    assert not output.exists()
    assert "Could not talk to the printer" in capsys.readouterr().err


async def test_cli_default_output(
    aresponses: ResponsesMockServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the default capture file name is derived from the host."""
    monkeypatch.chdir(tmp_path)
    _add_response(
        aresponses,
        load_fixture_binary("get-printer-attributes-epsonxp6000.bin"),
    )

    assert await run([DEFAULT_PRINTER_URI, "--ipp-version", "1.1"]) == EXIT_OK

    assert (tmp_path / f"ipp-{DEFAULT_PRINTER_HOST}.bin").exists()


def test_parse_version() -> None:
    """Test IPP version parsing."""
    assert _parse_version("2.0") == (2, 0)
    assert _parse_version("1.1") == (1, 1)

    with pytest.raises(SystemExit):
        main([DEFAULT_PRINTER_URI, "--ipp-version", "banana"])


def test_main_default_ipp_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main() drives run() through asyncio.run."""
    seen: list[list[str] | None] = []

    async def fake_run(argv: list[str] | None = None) -> int:
        seen.append(argv)
        return EXIT_OK

    monkeypatch.setattr("pyipp.__main__.run", fake_run)
    assert main(["ipp://example.local/ipp/print"]) == EXIT_OK
    assert seen == [["ipp://example.local/ipp/print"]]
