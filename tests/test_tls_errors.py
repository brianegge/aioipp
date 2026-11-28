"""Tests for reporting TLS handshake failures."""

import asyncio
import ssl
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from aiohttp import (
    ClientConnectorCertificateError,
    ClientConnectorSSLError,
    ClientSession,
)
from aiohttp.client_reqrep import ConnectionKey

from pyipp import IPP, IPPConnectionError, IPPConnectionTLSError
from pyipp.const import DEFAULT_PRINTER_ATTRIBUTES
from pyipp.enums import IppOperation

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# What a printer with no cipher suite in common sends back to the ClientHello:
# a TLS 1.2 fatal alert, handshake_failure (40).
HANDSHAKE_FAILURE_ALERT = bytes.fromhex("15030300020228")

CONNECTION_KEY = ConnectionKey(
    host="printer.example.com",
    port=631,
    is_ssl=True,
    ssl=False,
    proxy=None,
    proxy_auth=None,
    proxy_headers_hash=None,
)


@pytest.fixture
async def alert_server() -> AsyncIterator[int]:
    """Serve a TLS endpoint that rejects every handshake with an alert."""

    async def handle(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        await reader.read(65536)
        writer.write(HANDSHAKE_FAILURE_ALERT)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    async with server:
        yield server.sockets[0].getsockname()[1]


async def _get_printer_attributes(ipp: IPP) -> None:
    await ipp.execute(
        IppOperation.GET_PRINTER_ATTRIBUTES,
        {
            "operation-attributes-tag": {
                "requested-attributes": DEFAULT_PRINTER_ATTRIBUTES,
            },
        },
    )


async def test_handshake_failure_alert(alert_server: int) -> None:
    """Test a handshake_failure alert names the cause."""
    async with ClientSession() as session:
        ipp = IPP(
            host="127.0.0.1",
            port=alert_server,
            tls=True,
            verify_ssl=False,
            base_path="/ipp/print",
            session=session,
        )
        with pytest.raises(IPPConnectionTLSError) as err:
            await _get_printer_attributes(ipp)

    assert err.value.reason == "SSLV3_ALERT_HANDSHAKE_FAILURE"
    assert str(err.value) == (
        "TLS handshake with IPP server failed: SSLV3_ALERT_HANDSHAKE_FAILURE"
    )
    # Callers that only know IPPConnectionError keep working.
    assert isinstance(err.value, IPPConnectionError)


async def test_certificate_verify_failed() -> None:
    """Test a certificate verification failure includes OpenSSL's message."""
    cert_error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    cert_error.reason = "CERTIFICATE_VERIFY_FAILED"
    cert_error.verify_message = "self-signed certificate"

    session = AsyncMock(spec=ClientSession)
    session.request.side_effect = ClientConnectorCertificateError(
        CONNECTION_KEY,
        cert_error,
    )
    ipp = IPP("ipps://printer.example.com:631/ipp/print", session=session)

    with pytest.raises(IPPConnectionTLSError) as err:
        await _get_printer_attributes(ipp)

    assert err.value.reason == "CERTIFICATE_VERIFY_FAILED: self-signed certificate"


async def test_tls_error_without_reason() -> None:
    """Test a TLS failure with no OpenSSL reason falls back to the error text."""
    session = AsyncMock(spec=ClientSession)
    session.request.side_effect = ClientConnectorSSLError(
        CONNECTION_KEY,
        OSError("connection reset during handshake"),
    )
    ipp = IPP("ipps://printer.example.com:631/ipp/print", session=session)

    with pytest.raises(IPPConnectionTLSError) as err:
        await _get_printer_attributes(ipp)

    assert err.value.reason == "connection reset during handshake"
