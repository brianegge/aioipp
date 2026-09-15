"""Tests for Parser."""

import pytest
from syrupy.assertion import SnapshotAssertion

from pyipp import IPPParseError, enums, parser
from pyipp.const import DEFAULT_CHARSET, DEFAULT_CHARSET_LANGUAGE, DEFAULT_PROTO_VERSION
from pyipp.enums import IppOperation

from . import load_fixture_binary

RESPONSE_GET_PRINTER_ATTRIBUTES = load_fixture_binary(
    "get-printer-attributes-response-000.bin",
)

MOCK_IEEE1284_DEVICE_ID = "MFG:EPSON;CMD:ESCPL2,BDC,D4,D4PX,ESCPR7,END4,GENEP,URF;MDL:XP-6000 Series;CLS:PRINTER;DES:EPSON XP-6000 Series;CID:EpsonRGB;FID:FXN,DPA,WFA,ETN,AFN,DAN,WRA;RID:20;DDS:022500;ELG:1000;SN:583434593035343012;URF:CP1,PQ4-5,OB9,OFU0,RS360,SRGB24,W8,DM3,IS1-7-6,V1.4,MT1-3-7-8-10-11-12;"


def test_parse() -> None:
    """Test the parse method."""
    result = parser.parse(RESPONSE_GET_PRINTER_ATTRIBUTES)
    assert result == {
        "data": b"",
        "jobs": [],
        "operation-attributes": {
            "attributes-charset": DEFAULT_CHARSET,
            "attributes-natural-language": DEFAULT_CHARSET_LANGUAGE,
            "printer-uri": "ipp://printer.example.com:361/ipp/print",
            "requesting-user-name": "PythonIPP",
        },
        "printers": [],
        "request-id": 1,
        "status-code": IppOperation.GET_PRINTER_ATTRIBUTES,
        "unsupported-attributes": [],
        "version": DEFAULT_PROTO_VERSION,
    }


def test_parse_attribute() -> None:
    """Test the parse_attribute method."""
    result = parser.parse_attribute(RESPONSE_GET_PRINTER_ATTRIBUTES, 9)
    assert result == (
        {
            "name": "attributes-charset",
            "name-length": 18,
            "tag": 71,
            "value": "utf-8",
            "value-length": 5,
        },
        37,
    )


def test_parse_attribute_reserved_string() -> None:
    """Test the parse_attribute method when provided a reserved string."""
    result = parser.parse_attribute(b"C\x00\x0freserved-string\x00\x04yoda", 0)
    assert result == (
        {
            "name": "reserved-string",
            "name-length": 15,
            "tag": 67,
            "value": "yoda",
            "value-length": 4,
        },
        24,
    )

    result = parser.parse_attribute(b"C\x00\x0freserved-string\x00\x00", 0)
    assert result == (
        {
            "name": "reserved-string",
            "name-length": 15,
            "tag": 67,
            "value": None,
            "value-length": 0,
        },
        20,
    )


def test_parse_attribute_invalid_date() -> None:
    """Test the parse_attribute method when provided an invalid date."""
    invalid = b"1\x00\x14printer-current-time\x00\x0299"

    with pytest.raises(IPPParseError):
        parser.parse_attribute(invalid, 0)


def test_parse_ieee1284_device_id() -> None:
    """Test the parse_ieee1284_device_id method."""
    result = parser.parse_ieee1284_device_id(MOCK_IEEE1284_DEVICE_ID)

    assert result
    assert result["MFG"] == "EPSON"
    assert result["MDL"] == "XP-6000 Series"
    assert result["SN"] == "583434593035343012"
    assert result["CMD"] == "ESCPL2,BDC,D4,D4PX,ESCPR7,END4,GENEP,URF"

    assert result["MANUFACTURER"] == result["MFG"]
    assert result["MODEL"] == result["MDL"]
    assert result["COMMAND SET"] == result["CMD"]
    assert result["SERIALNUMBER"] == result["SN"]


def test_parse_ieee1284_device_id_serial_variants() -> None:
    """Test that vendor serial number spellings map to SERIALNUMBER."""
    # A real Kyocera TASKalfa MZ6001ci reports SER rather than SN.
    kyocera = parser.parse_ieee1284_device_id(
        "ID:TASKalfa MZ6001ci;MFG:Kyocera;MDL:TASKalfa MZ6001ci;SER:1FN6111961;",
    )
    assert kyocera["SERIALNUMBER"] == "1FN6111961"

    assert (
        parser.parse_ieee1284_device_id("MFG:Acme;SERN:ABC123;")["SERIALNUMBER"]
        == "ABC123"
    )

    # An explicit long form always wins over a short alias.
    both = parser.parse_ieee1284_device_id(
        "MFG:Acme;SERIALNUMBER:LONG1;SN:SHORT1;",
    )
    assert both["SERIALNUMBER"] == "LONG1"

    assert "SERIALNUMBER" not in parser.parse_ieee1284_device_id("MFG:Xerox;MDL:X;")


def test_parse_ieee1284_device_id_manufacturer_only() -> None:
    """Test the parse_ieee1284_device_id method with only a manufacturer."""
    result = parser.parse_ieee1284_device_id("MANUFACTURER:EPSON")

    assert result == {
        "MANUFACTURER": "EPSON",
    }


def test_parse_ieee1284_device_id_empty() -> None:
    """Test the parse_ieee1284_device_id method with empty string."""
    result = parser.parse_ieee1284_device_id("")

    assert isinstance(result, dict)


@pytest.mark.parametrize(
    "device_id",
    [
        "Unknown",
        "Unknown;",
        "not a device id",
        ";;",
    ],
)
def test_parse_ieee1284_device_id_malformed(device_id: str) -> None:
    """Test the parse_ieee1284_device_id method with a non-IEEE 1284 value.

    Some printers (e.g. SHARP MX-3060V / MX-3071) report "Unknown".
    """
    result = parser.parse_ieee1284_device_id(device_id)

    assert not result


def test_parse_ieee1284_device_id_partially_malformed() -> None:
    """Test the parse_ieee1284_device_id method skips segments without a colon."""
    result = parser.parse_ieee1284_device_id("MFG:SHARP;Unknown;MDL:MX-3071;;")

    assert result == {
        "MFG": "SHARP",
        "MDL": "MX-3071",
        "MANUFACTURER": "SHARP",
        "MODEL": "MX-3071",
    }


def test_parse_ieee1284_device_id_value_with_colons() -> None:
    """Test the parse_ieee1284_device_id method keeps colons inside values."""
    result = parser.parse_ieee1284_device_id("MFG:HP;URL:http://example.com:80/;")

    assert result["MFG"] == "HP"
    assert result["URL"] == "http://example.com:80/"


def test_parse_make_and_model() -> None:
    """Test the parse_make_and_model method."""
    result = parser.parse_make_and_model("")
    assert result == ("Unknown", "Unknown")

    # generic fallback for unknown brands
    result = parser.parse_make_and_model("IPP")
    assert result == ("IPP", "Unknown")

    result = parser.parse_make_and_model("IPP Printer")
    assert result == ("IPP", "Printer")

    # known brands
    result = parser.parse_make_and_model("EPSON XP-6000 Series")
    assert result == ("EPSON", "XP-6000 Series")

    result = parser.parse_make_and_model("HP Officejet Pro 6830")
    assert result == ("HP", "Officejet Pro 6830")

    result = parser.parse_make_and_model("HP Photosmart D110 Series")
    assert result == ("HP", "Photosmart D110 Series")


def test_parse_brother_mfcj5320dw(snapshot: SnapshotAssertion) -> None:
    """Test the parse method against response from Brother MFC-J5320DW."""
    response = load_fixture_binary("get-printer-attributes-brother-mfcj5320dw.bin")

    result = parser.parse(response)
    assert result == snapshot


def test_parse_epson_xp6000(snapshot: SnapshotAssertion) -> None:
    """Test the parse method against response from Epson XP-6000 Series."""
    response = load_fixture_binary("get-printer-attributes-epsonxp6000.bin")

    result = parser.parse(response)
    assert result == snapshot


def test_parse_kyocera_ecosys_m2540dn(snapshot: SnapshotAssertion) -> None:
    """Test the parse method against response from Kyocera Ecosys M2540DN."""
    response = load_fixture_binary(
        "get-printer-attributes-kyocera-ecosys-m2540dn-001.bin",
    )

    result = parser.parse(response)
    assert result == snapshot


def test_parse_empty_attribute_group(snapshot: SnapshotAssertion) -> None:
    """Test the parse method against a sample response with an empty attribute group."""
    response = load_fixture_binary(
        "get-printer-attributes-empty-attribute-group.bin",
    )

    result = parser.parse(response)
    assert result == snapshot


def test_parse_attribute_unknown_enum_value() -> None:
    """Test that an unknown enum value does not fail the whole response."""
    # finishings-default carrying 0x2710, a value no IPP revision defines.
    data = b"\x23\x00\x12finishings-default\x00\x04\x00\x00\x27\x10"
    result, _ = parser.parse_attribute(data, 0)

    assert result["value"] == 0x2710


def test_parse_attribute_known_enum_value() -> None:
    """Test that a known enum value is still resolved to its enum member."""
    # 0x0E is jog-offset, reported by the Xerox AltaLink C8135.
    data = b"\x23\x00\x12finishings-default\x00\x04\x00\x00\x00\x0e"
    result, _ = parser.parse_attribute(data, 0)

    assert result["value"] is enums.IppFinishing.JOG_OFFSET
