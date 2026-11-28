"""Exceptions for IPP."""


class IPPError(Exception):
    """Generic IPP exception."""


class IPPConnectionError(IPPError):
    """IPP connection exception."""


class IPPConnectionTLSError(IPPConnectionError):
    """TLS handshake with the IPP server failed.

    ``reason`` holds the short cause reported by OpenSSL, such as
    ``SSLV3_ALERT_HANDSHAKE_FAILURE`` (the printer shares no cipher suite or
    protocol version with the client) or ``CERTIFICATE_VERIFY_FAILED``.
    """

    def __init__(self, *args: object, reason: str) -> None:
        """Initialize the exception."""
        super().__init__(*args)
        self.reason = reason


class IPPConnectionUpgradeRequired(IPPError):  # noqa: N818
    """IPP connection upgrade requested."""


class IPPParseError(IPPError):
    """IPP parse exception.

    When the error comes from a printer response, ``scrubbed_response`` holds
    that response with identifying values masked (see ``pyipp.scrub``), and a
    note with an encoded copy is added for bug reports.
    """

    def __init__(
        self,
        *args: object,
        scrubbed_response: bytes | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(*args)
        self.scrubbed_response = scrubbed_response


class IPPResponseError(IPPError):
    """IPP response exception."""


class IPPVersionNotSupportedError(IPPError):
    """IPP version not supported."""
