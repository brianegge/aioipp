"""Exceptions for IPP."""


class IPPError(Exception):
    """Generic IPP exception."""


class IPPConnectionError(IPPError):
    """IPP connection exception."""


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
