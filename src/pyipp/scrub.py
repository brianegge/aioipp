"""Remove identifying values from raw IPP messages before they are shared."""

from __future__ import annotations

import logging
import re
import struct

from .enums import IppTag

_LOGGER = logging.getLogger(__name__)

# Attributes whose whole value is free text set by an administrator or user,
# or a name that printers commonly derive from their MAC address or serial
# number (e.g. Kyocera "KM38341C", HP "... [1E0C70]").
REDACTED_ATTRIBUTES = frozenset(
    {
        "contact-name",
        "contact-uri",
        "contact-vcard",
        "document-name",
        "document-name-supplied",
        "job-accounting-user-id",
        "job-name",
        "job-originating-host-name",
        "job-originating-user-name",
        "job-originating-user-uri",
        "job-password",
        "owner-name",
        "owner-uri",
        "owner-vcard",
        "printer-dns-sd-name",
        "printer-geo-location",
        "printer-info",
        "printer-location",
        "printer-name",
        "printer-organization",
        "printer-organizational-unit",
        "printer-serial-number",
        "requesting-user-name",
        "requesting-user-uri",
    },
)

# Value tags that carry octets or text. Every other value tag holds a number,
# date, boolean or range, which identify nothing and are left untouched.
_STRING_TAGS = frozenset(
    {
        IppTag.STRING,
        IppTag.TEXT,
        IppTag.NAME,
        IppTag.RESERVED_STRING,
        IppTag.KEYWORD,
        IppTag.URI,
        IppTag.URI_SCHEME,
        IppTag.CHARSET,
        IppTag.LANGUAGE,
        IppTag.MIME_TYPE,
        IppTag.MEMBER_NAME,
    },
)
_LANG_TAGS = frozenset({IppTag.TEXT_LANG, IppTag.NAME_LANG})

_UUID = re.compile(
    rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_MAC = re.compile(
    rb"(?<![0-9a-f])[0-9a-f]{2}(?:[:-][0-9a-f]{2}){5}(?![0-9a-f])",
    re.IGNORECASE,
)
_HEX_DIGIT = re.compile(rb"[0-9a-f]", re.IGNORECASE)
# Serial number segment of an IEEE 1284 device ID, e.g. "SN:VND1B47698;".
_DEVICE_ID_SERIAL = re.compile(
    rb"((?:^|;)\s*(?:SN|SERN|SERIALNUMBER|SERIAL)\s*:)([^;]*)",
    re.IGNORECASE,
)
# The authority of a URI, split into userinfo and host, and port. The port,
# path and query are kept.
_URI_AUTHORITY = re.compile(
    rb"([a-z][a-z0-9+.-]*://)([^/?#\s;,'\"]*?)((?::[0-9]+)?(?=[/?#\s;,'\"]|$))",
    re.IGNORECASE,
)


def _mask(value: bytes) -> bytes:
    """Return a mask of the same length as value."""
    return b"x" * len(value)


def _scrub_patterns(value: bytes) -> bytes:
    """Mask identifiers recognised by their shape, wherever they appear."""
    value = _UUID.sub(lambda m: _HEX_DIGIT.sub(b"0", m.group()), value)
    value = _MAC.sub(lambda m: _HEX_DIGIT.sub(b"0", m.group()), value)
    value = _DEVICE_ID_SERIAL.sub(lambda m: m.group(1) + _mask(m.group(2)), value)
    return _URI_AUTHORITY.sub(
        lambda m: m.group(1) + _mask(m.group(2)) + m.group(3),
        value,
    )


def _scrub_value(name: str, value: bytes) -> bytes:
    """Return the scrubbed form of a single text value."""
    if name in REDACTED_ATTRIBUTES:
        return _mask(value)

    return _scrub_patterns(value)


def scrub(data: bytes) -> bytes:
    """Return a copy of a raw IPP message with identifying values masked.

    Serial numbers, UUIDs, MAC addresses, URI hosts, and names, locations
    and other text that an administrator or user sets are replaced. Every
    replacement keeps the original length and only text values change, so
    the result parses exactly as the original did, including whatever made
    the original fail to parse.

    Only the attribute groups are scrubbed. Document data after the
    end-of-attributes tag is returned as is.

    Removal is best effort: vendor-specific attributes can carry anything.
    """
    out = bytearray(data)
    # Skip version, operation or status code, and request ID.
    offset = 8
    attribute_name = ""
    member_name = ""
    collections: list[tuple[str, str]] = []
    start = offset

    try:
        while (tag := out[offset]) != IppTag.END:
            start = offset
            if tag < IppTag.UNSUPPORTED_VALUE:
                # Delimiter for the next attribute group.
                offset += 1
                continue

            name_length = struct.unpack_from(">H", out, offset + 1)[0]
            offset += 3
            if name_length:
                attribute_name = out[offset : offset + name_length].decode(
                    "utf-8",
                    "replace",
                )
            offset += name_length

            value_length = struct.unpack_from(">H", out, offset)[0]
            offset += 2
            end = offset + value_length
            if end > len(out):
                msg = "value runs past the end of the message"
                raise IndexError(msg)  # noqa: TRY301

            effective_name = member_name if collections else attribute_name

            if tag == IppTag.BEGIN_COLLECTION:
                collections.append((attribute_name, member_name))
                member_name = ""
            elif tag == IppTag.END_COLLECTION:
                if collections:
                    attribute_name, member_name = collections.pop()
            elif tag == IppTag.MEMBER_NAME:
                member_name = out[offset:end].decode("utf-8", "replace")
            elif tag in _STRING_TAGS:
                out[offset:end] = _scrub_value(effective_name, bytes(out[offset:end]))
            elif tag in _LANG_TAGS and value_length >= 4:
                language_length = struct.unpack_from(">H", out, offset)[0]
                text_start = offset + 2 + language_length + 2
                if text_start <= end:
                    out[text_start:end] = _scrub_value(
                        effective_name,
                        bytes(out[text_start:end]),
                    )

            offset = end
    except IndexError, struct.error:
        # The message is malformed or truncated. Fall back to masking what can
        # be recognised by shape from here to the end.
        _LOGGER.debug("Unable to walk IPP message at offset %s", start)
        out[start:] = _scrub_patterns(bytes(out[start:]))

    return bytes(out)
