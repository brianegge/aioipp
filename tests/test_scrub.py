"""Tests for removing identifying values from raw IPP messages."""

from __future__ import annotations

import re
import struct
from pathlib import Path
from typing import Any

import pytest

from pyipp import Printer, parser
from pyipp.enums import IppTag
from pyipp.scrub import REDACTED_ATTRIBUTES, scrub

from . import load_fixture_binary

FIXTURES = sorted(
    path.name for path in (Path(__file__).parent / "fixtures").glob("*.bin")
)

HEADER = struct.pack(">bbhi", 2, 0, 0, 1)


def _attr(tag: int, name: str, value: bytes) -> bytes:
    """Encode a single attribute."""
    encoded = name.encode()
    return (
        struct.pack(">bh", tag, len(encoded))
        + encoded
        + struct.pack(">h", len(value))
        + value
    )


def _text_lang(language: str, text: str) -> bytes:
    """Encode a textWithLanguage value."""
    return (
        struct.pack(">h", len(language))
        + language.encode()
        + struct.pack(">h", len(text.encode()))
        + text.encode()
    )


def _message(*attributes: bytes, data: bytes = b"") -> bytes:
    """Encode a response with one printer attribute group."""
    return (
        HEADER
        + bytes([IppTag.OPERATION])
        + _attr(IppTag.CHARSET, "attributes-charset", b"utf-8")
        + bytes([IppTag.PRINTER])
        + b"".join(attributes)
        + bytes([IppTag.END])
        + data
    )


def _printer(raw: bytes) -> dict[str, Any]:
    """Parse a message and return its printer attributes."""
    printer: dict[str, Any] = parser.parse(raw)["printers"][0]
    return printer


def _leaves(obj: Any, path: str = "") -> dict[str, Any]:
    """Flatten parsed data to path -> value."""
    if isinstance(obj, dict):
        return {
            key: value
            for name, child in obj.items()
            for key, value in _leaves(child, f"{path}/{name}").items()
        }
    if isinstance(obj, list):
        return {
            key: value
            for index, child in enumerate(obj)
            for key, value in _leaves(child, f"{path}[{index}]").items()
        }
    return {path: obj}


def _identifiers(parsed: dict[str, Any]) -> set[str]:
    """Collect identifying values from parsed data, independently of scrub."""
    found: set[str] = set()
    redacted: set[str] = set()
    kept: list[str] = []
    for path, value in _leaves(parsed).items():
        if not isinstance(value, str):
            continue
        name = re.split(r"[/\[]", path.rsplit("/", 1)[-1])[0]
        if name in REDACTED_ATTRIBUTES:
            redacted.add(value)
        else:
            kept.append(value)
        found.update(re.findall(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value))
        found.update(re.findall(r"(?:^|;)\s*SN:([^;]*)", value))
        found.update(re.findall(r"://([^/:?#]+)", value))
    # A printer-info of "EPSON XP-6000 Series" is also in printer-make-and-model,
    # which is kept on purpose.
    found.update(value for value in redacted if not any(value in k for k in kept))
    # Short values such as "doc" also occur inside unrelated keywords.
    return {value for value in found if len(value) >= 6}


@pytest.mark.parametrize("fixture", FIXTURES)
def test_scrub_fixture_keeps_structure(fixture: str) -> None:
    """Scrubbing only changes text, so everything else parses identically."""
    raw = load_fixture_binary(fixture)
    scrubbed = scrub(raw)

    assert len(scrubbed) == len(raw)

    before = _leaves(parser.parse(raw))
    after = _leaves(parser.parse(scrubbed))
    assert before.keys() == after.keys()
    for path, value in before.items():
        if not isinstance(value, str):
            assert after[path] == value, path


@pytest.mark.parametrize("fixture", FIXTURES)
def test_scrub_fixture_removes_identifiers(fixture: str) -> None:
    """No serial number, UUID, host or administrator text survives."""
    raw = load_fixture_binary(fixture)
    scrubbed = scrub(raw)

    for identifier in _identifiers(parser.parse(raw)):
        assert identifier.encode() not in scrubbed, identifier


def test_scrub_fixture_keeps_useful_values() -> None:
    """Make, model, firmware and state survive for bug reports."""
    raw = load_fixture_binary("get-printer-attributes-epsonxp6000.bin")
    printer = Printer.from_dict(_printer(scrub(raw)))

    assert printer.info.manufacturer == "EPSON"
    assert printer.info.model == "XP-6000 Series"
    assert printer.info.serial == "xxxxxxxxxxxxxxxxxx"
    assert printer.info.uuid == "00000000-0000-0000-0000-000000000000"
    assert printer.state.printer_state == "idle"
    assert [marker.level for marker in printer.markers] == [
        marker.level for marker in Printer.from_dict(_printer(raw)).markers
    ]


def test_scrub_device_id_serial() -> None:
    """Only the serial number segment of the device ID is masked."""
    raw = _message(
        _attr(
            IppTag.TEXT,
            "printer-device-id",
            b"MFG:HP;MDL:LaserJet;SN:VND1B47698;SERN:12345;CLS:PRINTER;",
        ),
    )

    assert _printer(scrub(raw))["printer-device-id"] == (
        "MFG:HP;MDL:LaserJet;SN:xxxxxxxxxx;SERN:xxxxx;CLS:PRINTER;"
    )


def test_scrub_uri_host() -> None:
    """URI hosts and credentials are masked, ports and paths are kept."""
    raw = _message(
        _attr(IppTag.URI, "printer-uri-supported", b"ipps://printer.lan:631/ipp"),
        _attr(IppTag.URI, "", b"ipp://user:secret@10.0.0.5/ipp/print"),
        _attr(IppTag.URI, "", b"ipp://[fe80::1]:631/ipp/print"),
        _attr(IppTag.URI, "", b"http://10.0.0.5"),
    )

    assert _printer(scrub(raw))["printer-uri-supported"] == [
        "ipps://xxxxxxxxxxx:631/ipp",
        "ipp://xxxxxxxxxxxxxxxxxxxx/ipp/print",
        "ipp://xxxxxxxxx:631/ipp/print",
        "http://xxxxxxxx",
    ]


def test_scrub_patterns_in_free_text() -> None:
    """MAC addresses, UUIDs and URIs are masked in any text attribute."""
    raw = _message(
        _attr(
            IppTag.TEXT,
            "printer-state-message",
            b"MAC 00:1B:63:84:45:E6 uuid 3e5a7237-ad6c-4ef0-be85-d0cc5d4f7721 "
            b"see http://printer.lan/status",
        ),
    )

    assert _printer(scrub(raw))["printer-state-message"] == (
        "MAC 00:00:00:00:00:00 uuid 00000000-0000-0000-0000-000000000000 "
        "see http://xxxxxxxxxxx/status"
    )


def test_scrub_text_with_language() -> None:
    """Only the text part of a textWithLanguage value is masked."""
    raw = _message(
        _attr(IppTag.TEXT_LANG, "printer-location", _text_lang("en", "Boiler Room")),
        _attr(IppTag.TEXT_LANG, "printer-state-message", _text_lang("en", "Ready")),
    )

    scrubbed = _printer(scrub(raw))

    assert scrubbed["printer-location"] == "xxxxxxxxxxx"
    assert scrubbed["printer-state-message"] == "Ready"


def test_scrub_collection_members() -> None:
    """Collection members are matched by member name, including nested ones."""
    raw = _message(
        _attr(IppTag.BEGIN_COLLECTION, "printer-contact-col", b""),
        _attr(IppTag.MEMBER_NAME, "", b"contact-name"),
        _attr(IppTag.NAME, "", b"Alice"),
        _attr(IppTag.MEMBER_NAME, "", b"nested"),
        _attr(IppTag.BEGIN_COLLECTION, "", b""),
        _attr(IppTag.MEMBER_NAME, "", b"contact-vcard"),
        _attr(IppTag.TEXT, "", b"BEGIN:VCARD"),
        _attr(IppTag.END_COLLECTION, "", b""),
        _attr(IppTag.MEMBER_NAME, "", b"media-type"),
        _attr(IppTag.KEYWORD, "", b"stationery"),
        _attr(IppTag.END_COLLECTION, "", b""),
        _attr(IppTag.NAME, "printer-name", b"KM38341C"),
        _attr(IppTag.NAME, "", b"second-name"),
        _attr(IppTag.KEYWORD, "printer-state-reasons", b"none"),
    )

    scrubbed = _printer(scrub(raw))

    assert scrubbed["printer-contact-col"] == {
        "contact-name": "xxxxx",
        "nested": {"contact-vcard": "xxxxxxxxxxx"},
        "media-type": "stationery",
    }
    assert scrubbed["printer-name"] == ["xxxxxxxx", "xxxxxxxxxxx"]
    assert scrubbed["printer-state-reasons"] == "none"


def test_scrub_keeps_document_data() -> None:
    """Data after the end-of-attributes tag is not touched."""
    document = b"SN:ABCDEF;http://printer.lan/"
    raw = _message(_attr(IppTag.NAME, "printer-name", b"office"), data=document)

    assert scrub(raw).endswith(document)


def test_scrub_keeps_parse_failure() -> None:
    """A response that fails to parse still fails the same way once scrubbed."""
    enum = struct.pack(">i", 3)
    raw = _message(
        _attr(IppTag.ENUM, "printer-state", enum),
        _attr(IppTag.ENUM, "", enum),
        _attr(IppTag.NAME, "printer-name", b"KM38341C"),
    )

    for message in (raw, scrub(raw)):
        with pytest.raises(TypeError, match="unhashable"):
            Printer.from_dict(_printer(message))


@pytest.mark.parametrize(
    "raw",
    [
        # Value length runs past the end of the message.
        _message(_attr(IppTag.TEXT, "printer-info", b"x"))[:-4]
        + b"\x00\x40 uuid 3e5a7237-ad6c-4ef0-be85-d0cc5d4f7721",
        # Message ends without an end-of-attributes tag.
        HEADER
        + bytes([IppTag.PRINTER])
        + _attr(IppTag.URI, "printer-uri", b"ipp://printer.lan/ipp")
        + b" 3e5a7237-ad6c-4ef0-be85-d0cc5d4f7721",
    ],
)
def test_scrub_malformed_message(raw: bytes) -> None:
    """Malformed messages fall back to masking by pattern."""
    scrubbed = scrub(raw)

    assert len(scrubbed) == len(raw)
    assert b"3e5a7237" not in scrubbed
    assert b"00000000-0000-0000-0000-000000000000" in scrubbed


def test_scrub_tolerates_bad_nesting() -> None:
    """Stray collection ends and oversized languages do not stop the walk."""
    raw = _message(
        _attr(IppTag.END_COLLECTION, "", b""),
        _attr(IppTag.TEXT_LANG, "printer-location", b"\x00\x10en\x00\x01x"),
        _attr(IppTag.NAME, "printer-name", b"KM38341C"),
    )

    scrubbed = scrub(raw)

    assert len(scrubbed) == len(raw)
    assert b"KM38341C" not in scrubbed


def test_scrub_short_message() -> None:
    """Messages too short to hold a header are returned unchanged."""
    assert scrub(b"\x02\x00") == b"\x02\x00"
