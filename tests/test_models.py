"""Tests for IPP Models."""

# pylint: disable=R0912,R0915
from __future__ import annotations

from typing import Any

import pytest

from pyipp import models, parser

from . import IPPE10_PRINTER_ATTRS, load_fixture_binary


@pytest.mark.asyncio
async def test_info() -> None:  # noqa: PLR0915
    """Test Info model."""
    parsed = parser.parse(load_fixture_binary("get-printer-attributes-epsonxp6000.bin"))
    data = parsed["printers"][0]
    info = models.Info.from_dict(data)

    assert info
    assert info.command_set == "ESCPL2,BDC,D4,D4PX,ESCPR7,END4,GENEP,URF"
    assert info.location == ""
    assert info.name == "EPSON XP-6000 Series"
    assert info.manufacturer == "EPSON"
    assert info.model == "XP-6000 Series"
    assert info.printer_name == "ipp/print"
    assert info.printer_info == "EPSON XP-6000 Series"
    assert info.printer_uri_supported == [
        "ipps://192.168.1.92:631/ipp/print",
        "ipp://192.168.1.92:631/ipp/print",
    ]
    assert info.more_info == "http://192.168.1.92:80/PRESENTATION/BONJOUR"
    assert info.serial == "583434593035343012"
    assert info.uuid == "cfe92100-67c4-11d4-a45f-f8d027761251"
    assert info.version == "20.44.NU25M7"
    assert info.uptime == 783801

    # no make/model, device id
    data["printer-make-and-model"] = ""
    info = models.Info.from_dict(data)

    assert info
    assert info.name == "EPSON XP-6000 Series"
    assert info.printer_name == "ipp/print"
    assert info.manufacturer == "EPSON"
    assert info.model == "XP-6000 Series"

    # no make/model, no device id, URI name
    data["printer-device-id"] = ""
    data["printer-make-and-model"] = ""
    data["printer-name"] = "ipp/print"
    info = models.Info.from_dict(data)

    assert info
    assert info.name == "IPP Printer"
    assert info.printer_name == "ipp/print"
    assert info.manufacturer == "Unknown"
    assert info.model == "Unknown"

    # no make/model, no device id, name
    data["printer-device-id"] = ""
    data["printer-make-and-model"] = ""
    data["printer-name"] = "Printy"
    info = models.Info.from_dict(data)

    assert info
    assert info.name == "Printy"
    assert info.printer_name == "Printy"
    assert info.manufacturer == "Unknown"
    assert info.model == "Unknown"

    # no make/model, no device id, no name
    data["printer-device-id"] = ""
    data["printer-make-and-model"] = ""
    data["printer-name"] = ""
    info = models.Info.from_dict(data)

    assert info
    assert info.name == "IPP Printer"
    assert info.printer_name == ""
    assert info.manufacturer == "Unknown"
    assert info.model == "Unknown"


@pytest.mark.asyncio
async def test_state() -> None:
    """Test State model."""
    data: dict[str, Any] = {
        "printer-state": 4,
        "printer-state-reasons": "none",
    }

    state = models.State.from_dict(data)

    assert state
    assert state.printer_state == "printing"
    assert state.reasons is None
    assert state.message is None


@pytest.mark.asyncio
async def test_printer() -> None:  # noqa: PLR0915
    """Test Printer model."""
    parsed = parser.parse(load_fixture_binary("get-printer-attributes-epsonxp6000.bin"))
    printer = models.Printer.from_dict(parsed["printers"][0])

    assert printer

    assert printer.info
    assert printer.info.command_set == "ESCPL2,BDC,D4,D4PX,ESCPR7,END4,GENEP,URF"
    assert printer.info.location == ""
    assert printer.info.name == "EPSON XP-6000 Series"
    assert printer.info.manufacturer == "EPSON"
    assert printer.info.model == "XP-6000 Series"
    assert printer.info.printer_name == "ipp/print"
    assert printer.info.printer_info == "EPSON XP-6000 Series"
    assert printer.info.printer_uri_supported == [
        "ipps://192.168.1.92:631/ipp/print",
        "ipp://192.168.1.92:631/ipp/print",
    ]
    assert printer.info.more_info == "http://192.168.1.92:80/PRESENTATION/BONJOUR"
    assert printer.info.serial == "583434593035343012"
    assert printer.info.uuid == "cfe92100-67c4-11d4-a45f-f8d027761251"
    assert printer.info.version == "20.44.NU25M7"
    assert printer.info.uptime == 783801

    assert printer.state
    assert printer.state.printer_state == "idle"
    assert printer.state.reasons == "marker-supply-low-warning"
    assert printer.state.message is None

    assert printer.markers
    assert isinstance(printer.markers, list)
    assert len(printer.markers) == 5

    assert printer.markers[0]
    assert printer.markers[0].marker_id == 4
    assert printer.markers[0].marker_type == "ink-cartridge"
    assert printer.markers[0].name == "Black ink"
    assert printer.markers[0].color == "#000000"
    assert printer.markers[0].level == 64
    assert printer.markers[0].low_level == 15
    assert printer.markers[0].high_level == 100

    assert printer.markers[1]
    assert printer.markers[1].marker_id == 1
    assert printer.markers[1].marker_type == "ink-cartridge"
    assert printer.markers[1].name == "Cyan ink"
    assert printer.markers[1].color == "#00FFFF"
    assert printer.markers[1].level == 99
    assert printer.markers[1].low_level == 15
    assert printer.markers[1].high_level == 100

    assert printer.markers[2]
    assert printer.markers[2].marker_id == 2
    assert printer.markers[2].marker_type == "ink-cartridge"
    assert printer.markers[2].name == "Magenta ink"
    assert printer.markers[2].color == "#FF00FF"
    assert printer.markers[2].level == 83
    assert printer.markers[2].low_level == 15
    assert printer.markers[2].high_level == 100

    assert printer.markers[3]
    assert printer.markers[3].marker_id == 0
    assert printer.markers[3].marker_type == "ink-cartridge"
    assert printer.markers[3].name == "Photo Black ink"
    assert printer.markers[3].color == "#000000"
    assert printer.markers[3].level == 27
    assert printer.markers[3].low_level == 15
    assert printer.markers[3].high_level == 100

    assert printer.markers[4]
    assert printer.markers[4].marker_id == 3
    assert printer.markers[4].marker_type == "ink-cartridge"
    assert printer.markers[4].name == "Yellow ink"
    assert printer.markers[4].color == "#FFFF00"
    assert printer.markers[4].level == 6
    assert printer.markers[4].low_level == 15
    assert printer.markers[4].high_level == 100

    assert printer.uris
    assert isinstance(printer.uris, list)
    assert len(printer.uris) == 2

    assert printer.uris[0]
    assert printer.uris[0].uri == "ipps://192.168.1.92:631/ipp/print"
    assert printer.uris[0].authentication is None
    assert printer.uris[0].security == "tls"

    assert printer.uris[1]
    assert printer.uris[1].uri == "ipp://192.168.1.92:631/ipp/print"
    assert printer.uris[1].authentication is None
    assert printer.uris[1].security is None


def test_printer_as_dict() -> None:
    """Test the dictionary version of Printer."""
    parsed = parser.parse(load_fixture_binary("get-printer-attributes-epsonxp6000.bin"))
    printer = models.Printer.from_dict(parsed["printers"][0])

    assert printer

    printer_dict = printer.as_dict()
    assert printer_dict
    assert isinstance(printer_dict, dict)
    assert isinstance(printer_dict["info"], dict)
    assert isinstance(printer_dict["state"], dict)
    assert isinstance(printer_dict["markers"], list)
    assert len(printer_dict["markers"]) == 5
    assert isinstance(printer_dict["uris"], list)
    assert len(printer_dict["uris"]) == 2


def test_printer_update_from_dict() -> None:
    """Test updating data of Printer."""
    parsed = parser.parse(load_fixture_binary("get-printer-attributes-epsonxp6000.bin"))
    printer = models.Printer.from_dict(parsed["printers"][0])

    assert printer
    assert printer.info
    assert printer.info.uptime == 783801

    parsed["printer-up-time"] = 2
    printer.update_from_dict(parsed)

    assert printer
    assert printer.info
    assert printer.info.uptime == 2


@pytest.mark.asyncio
async def test_printer_with_single_marker() -> None:
    """Test Printer model with single marker."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["marker-names"] = "Black"
    data["marker-types"] = "ink-cartridge"
    data["marker-colors"] = "#FF0000"
    data["marker-levels"] = 77
    data["marker-high-levels"] = 100
    data["marker-low-levels"] = 0

    printer = models.Printer.from_dict(data)
    assert printer
    assert printer.markers[0]
    assert printer.markers[0].name == "Black"
    assert printer.markers[0].color == "#FF0000"
    assert printer.markers[0].level == 77
    assert printer.markers[0].high_level == 100
    assert printer.markers[0].low_level == 0
    assert printer.markers[0].marker_type == "ink-cartridge"


@pytest.mark.asyncio
async def test_printer_with_single_marker_empty_strings() -> None:
    """Test Printer model with single marker with empty string values."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["marker-names"] = ""
    data["marker-types"] = ""
    data["marker-colors"] = ""
    data["marker-levels"] = ""
    data["marker-low-levels"] = ""
    data["marker-high-levels"] = ""

    printer = models.Printer.from_dict(data)
    assert printer
    assert len(printer.markers) == 0


@pytest.mark.asyncio
async def test_printer_with_single_marker_invalid() -> None:
    """Test Printer model with single invalid marker name."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["marker-names"] = -1

    printer = models.Printer.from_dict(data)
    assert printer
    assert len(printer.markers) == 0


@pytest.mark.asyncio
async def test_printer_with_extra_marker_data() -> None:
    """Test Printer model with extra marker data."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["marker-names"] = ["Black"]
    data["marker-types"] = ["ink-cartridge", "ink"]
    data["marker-colors"] = ["#FF0000", "#FF1111"]
    data["marker-levels"] = [99, 33]
    data["marker-low-levels"] = [0, 10]
    data["marker-high-levels"] = [99, 100]

    printer = models.Printer.from_dict(data)
    assert printer
    assert len(printer.markers) == 1
    assert printer.markers[0]
    assert printer.markers[0].name == "Black"
    assert printer.markers[0].color == "#FF0000"
    assert printer.markers[0].level == 99
    assert printer.markers[0].high_level == 99
    assert printer.markers[0].low_level == 0
    assert printer.markers[0].marker_type == "ink-cartridge"


@pytest.mark.asyncio
async def test_printer_with_single_supported_uri() -> None:
    """Test Printer model with single supported uri."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-uri-supported"] = "ipp://10.104.12.95:631/ipp/print"
    data["uri-authentication-supported"] = "none"
    data["uri-security-supported"] = "none"

    printer = models.Printer.from_dict(data)
    assert printer
    assert printer.uris[0]
    assert printer.uris[0].uri == "ipp://10.104.12.95:631/ipp/print"
    assert printer.uris[0].authentication is None
    assert printer.uris[0].security is None


@pytest.mark.asyncio
async def test_printer_with_single_supported_uri_extra_data() -> None:
    """Test Printer model with single supported uri with extra data."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-uri-supported"] = "ipp://10.104.12.95:631/ipp/print"
    data["uri-authentication-supported"] = ["none", "basic"]
    data["uri-security-supported"] = ["none", "tls"]

    printer = models.Printer.from_dict(data)
    assert printer
    assert printer.uris[0]
    assert printer.uris[0].uri == "ipp://10.104.12.95:631/ipp/print"
    assert printer.uris[0].authentication is None
    assert printer.uris[0].security is None


@pytest.mark.asyncio
async def test_printer_with_single_supported_uri_invalid_uri() -> None:
    """Test Printer model with single invalid supported uri."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-uri-supported"] = -1
    data["uri-authentication-supported"] = "none"
    data["uri-security-supported"] = "none"

    printer = models.Printer.from_dict(data)
    assert printer
    assert len(printer.uris) == 0


@pytest.mark.asyncio
async def test_counters() -> None:
    """Test Counters model."""
    data: dict[str, Any] = {
        "printer-impressions-completed": 1234,
        "printer-pages-completed": 5678,
        "printer-media-sheets-completed": 9012,
    }

    counters = models.Counters.from_dict(data)

    assert counters
    assert counters.impressions_completed == 1234
    assert not counters.impressions_completed_col
    assert counters.pages_completed == 5678
    assert counters.media_sheets_completed == 9012
    assert counters.supported == (
        "impressions_completed",
        "pages_completed",
        "media_sheets_completed",
    )


@pytest.mark.asyncio
async def test_counters_defaults() -> None:
    """Test Counters model with missing data."""
    counters = models.Counters.from_dict({})

    assert counters
    assert counters.impressions_completed is None
    assert not counters.impressions_completed_col
    assert counters.pages_completed is None
    assert counters.media_sheets_completed is None
    assert not counters.supported


@pytest.mark.asyncio
async def test_counters_out_of_band() -> None:
    """Test Counters model keeps out-of-band values as None but supported.

    The parser decodes out-of-band values (unknown, no-value) as strings.
    """
    data: dict[str, Any] = {
        "printer-impressions-completed": "",
        "printer-pages-completed": "",
        "printer-media-sheets-completed": 42,
        "printer-impressions-completed-col": {
            "monochrome": 7,
            "full-color": "",
        },
    }

    counters = models.Counters.from_dict(data)

    assert counters.impressions_completed is None
    assert counters.impressions_completed_col == {"monochrome": 7, "full-color": None}
    assert counters.pages_completed is None
    assert counters.media_sheets_completed == 42
    assert counters.supported == (
        "impressions_completed",
        "pages_completed",
        "media_sheets_completed",
    )


@pytest.mark.asyncio
async def test_counters_col_out_of_band() -> None:
    """Test Counters model with an out-of-band collection."""
    counters = models.Counters.from_dict(
        {"printer-impressions-completed-col": ""},
    )

    assert counters.impressions_completed is None
    assert not counters.impressions_completed_col
    assert counters.supported == ("impressions_completed",)


@pytest.mark.asyncio
async def test_counters_col() -> None:
    """Test Counters model with collection-based impressions."""
    data: dict[str, Any] = {
        "printer-impressions-completed-col": {
            "monochrome": 0,
            "full-color": 10,
        },
    }

    counters = models.Counters.from_dict(data)

    assert counters
    assert counters.impressions_completed == 10
    assert counters.impressions_completed_col == {"monochrome": 0, "full-color": 10}
    assert counters.supported == ("impressions_completed",)


@pytest.mark.asyncio
async def test_counters_col_incomplete_has_no_total() -> None:
    """Test an incomplete collection does not produce an impressions total."""
    data: dict[str, Any] = {
        "printer-impressions-completed-col": {
            "monochrome": 100,
            "full-color": "",
        },
    }

    counters = models.Counters.from_dict(data)

    assert counters.impressions_completed is None
    assert counters.impressions_completed_col == {"monochrome": 100, "full-color": None}


@pytest.mark.asyncio
async def test_counters_col_does_not_override_scalar() -> None:
    """Test that scalar impressions-completed takes precedence over col."""
    data: dict[str, Any] = {
        "printer-impressions-completed": 500,
        "printer-impressions-completed-col": {
            "monochrome": 100,
            "full-color": 200,
        },
    }

    counters = models.Counters.from_dict(data)

    assert counters.impressions_completed == 500
    assert counters.impressions_completed_col == {"monochrome": 100, "full-color": 200}


@pytest.mark.asyncio
async def test_printer_counters() -> None:
    """Test Printer model includes counters."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-impressions-completed"] = 500
    data["printer-pages-completed"] = 400
    data["printer-media-sheets-completed"] = 300

    printer = models.Printer.from_dict(data)
    assert printer
    assert printer.counters.impressions_completed == 500
    assert printer.counters.pages_completed == 400
    assert printer.counters.media_sheets_completed == 300


@pytest.mark.asyncio
async def test_printer_counters_in_as_dict() -> None:
    """Test Printer as_dict includes counters."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-impressions-completed"] = 100

    printer = models.Printer.from_dict(data)
    printer_dict = printer.as_dict()
    assert "counters" in printer_dict
    assert printer_dict["counters"]["impressions_completed"] == 100


@pytest.mark.asyncio
async def test_printer_with_single_supported_uri_with_security() -> None:
    """Test Printer model with multiple markers."""
    data = IPPE10_PRINTER_ATTRS.copy()
    data["printer-uri-supported"] = "ipps://10.104.12.95:631/ipp/print"
    data["uri-authentication-supported"] = "basic"
    data["uri-security-supported"] = "tls"

    printer = models.Printer.from_dict(data)
    assert printer
    assert printer.uris[0]
    assert printer.uris[0].uri == "ipps://10.104.12.95:631/ipp/print"
    assert printer.uris[0].authentication == "basic"
    assert printer.uris[0].security == "tls"


def test_info_malformed_device_id() -> None:
    """Test Info model with a non-IEEE 1284 printer-device-id.

    SHARP MX-3060V / MX-3071 report the literal string "Unknown".
    """
    info = models.Info.from_dict(
        {
            "printer-name": "ipp/print",
            "printer-make-and-model": "SHARP MX-3071",
            "printer-device-id": "Unknown",
            "printer-uri-supported": ["ipp://192.168.1.10:631/ipp/print"],
        },
    )

    assert info
    assert info.name == "SHARP MX-3071"
    assert info.manufacturer == "SHARP"
    assert info.model == "MX-3071"
    assert info.command_set is None
    assert info.serial is None


def test_info_firmware_version_list() -> None:
    """Test firmware version is joined into a single string when a list."""
    info = models.Info.from_dict(
        {
            "printer-name": "Lexmark MC2425adw",
            "printer-firmware-string-version": [
                "2.0",
                "1.02",
                "1.7",
                "1.5",
                "CXNZJ.250.038",
            ],
        },
    )

    assert info.version == "2.0, 1.02, 1.7, 1.5, CXNZJ.250.038"


def test_info_firmware_version_variants() -> None:
    """Test firmware version normalization for other value shapes."""
    assert models.Info.from_dict({}).version is None
    assert (
        models.Info.from_dict({"printer-firmware-string-version": []}).version is None
    )
    assert (
        models.Info.from_dict({"printer-firmware-string-version": ["", "1.13"]}).version
        == "1.13"
    )
    assert (
        models.Info.from_dict({"printer-firmware-string-version": 105}).version == "105"
    )


def test_tray_from_string() -> None:
    """Test Tray model parsing of a PWG key=value tray string."""
    # A real Xerox AltaLink C8135 input tray.
    tray = models.Tray.from_string(
        "type=sheetFeedAutoRemovableTray;mediafeed=21590;mediaxfeed=27940;"
        "maxcapacity=520;level=130;status=0;name=Tray1",
    )

    assert tray.name == "Tray1"
    assert tray.tray_type == "sheetFeedAutoRemovableTray"
    assert tray.level == 130
    assert tray.max_capacity == 520
    assert tray.status == 0


def test_tray_out_of_band_values() -> None:
    """Test that out-of-band tray levels become None rather than a count."""
    # A real Epson ET-2980 feeder, which reports neither level nor capacity.
    tray = models.Tray.from_string(
        "type=sheetFeedAutoNonRemovableTray;dimunit=micrometers;mediafeed=279400;"
        "maxcapacity=-2;level=-2;status=0;name=Rear Auto Sheet Feeder;",
    )

    assert tray.name == "Rear Auto Sheet Feeder"
    assert tray.level is None
    assert tray.max_capacity is None


def test_tray_repeated_keys() -> None:
    """Test that a repeated key keeps the first value.

    A real Kyocera TASKalfa MZ6001ci repeats mediafeed/mediaxfeed per tray.
    """
    tray = models.Tray.from_string(
        "type=other;mediafeed=85000;mediaxfeed=110000;mediafeed=110000;"
        "mediaxfeed=85000;maxcapacity=150;level=0;name=MP Tray",
    )

    assert tray.tray_type == "other"
    assert tray.level == 0
    assert tray.max_capacity == 150


def test_tray_garbage() -> None:
    """Test that an unparsable tray string does not raise."""
    tray = models.Tray.from_string("Unknown")

    assert tray.name is None
    assert tray.tray_type is None
    assert tray.level is None


def test_status() -> None:
    """Test Status model."""
    status = models.Status.from_dict(
        {
            "printer-is-accepting-jobs": True,
            "queued-job-count": 3,
            "printer-alert-description": ["Tray 5 (Bypass) is empty.", "Ready."],
            "media-ready": "na_letter_8.5x11in",
        },
    )

    assert status.accepting_jobs is True
    assert status.queued_jobs == 3
    assert status.alerts == ["Tray 5 (Bypass) is empty.", "Ready."]
    # A 1setOf reported as a bare value is still a list
    assert status.media_ready == ["na_letter_8.5x11in"]
    assert status.supported == (
        "accepting_jobs",
        "queued_jobs",
        "alerts",
        "media_ready",
    )


def test_status_defaults() -> None:
    """Test that a printer reporting nothing supports nothing."""
    status = models.Status.from_dict({})

    assert status.accepting_jobs is None
    assert status.queued_jobs is None
    assert status.alerts == []
    assert status.media_ready == []
    assert status.supported == ()


def test_status_out_of_band() -> None:
    """Test that out-of-band values are not mistaken for data.

    The attribute is still reported, so it stays in ``supported``.
    """
    status = models.Status.from_dict(
        {"queued-job-count": "unknown", "printer-is-accepting-jobs": "unknown"},
    )

    assert status.queued_jobs is None
    assert status.accepting_jobs is None
    assert "queued_jobs" in status.supported
    # A non-boolean cannot be reported as a supported boolean
    assert "accepting_jobs" not in status.supported


def test_info_icons_and_speed() -> None:
    """Test the static Info fields added for printer icons and speed."""
    info = models.Info.from_dict(
        {
            "printer-icons": [
                "https://192.168.1.158/printer-icon/machine_128.png",
                "https://192.168.1.158/printer-icon/machine_512.png",
            ],
            "pages-per-minute": 60,
            "pages-per-minute-color": 60,
        },
    )

    assert info.icons == [
        "https://192.168.1.158/printer-icon/machine_128.png",
        "https://192.168.1.158/printer-icon/machine_512.png",
    ]
    assert info.pages_per_minute == 60
    assert info.pages_per_minute_color == 60


def test_info_single_icon() -> None:
    """Test that a single icon reported as a bare value becomes a list."""
    info = models.Info.from_dict(
        {"printer-icons": "http://192.168.1.64/images/printer-icon128.png"},
    )

    assert info.icons == ["http://192.168.1.64/images/printer-icon128.png"]


def test_info_no_icons() -> None:
    """Test that a printer reporting no icons yields an empty list."""
    info = models.Info.from_dict({})

    assert info.icons == []
    assert info.pages_per_minute is None
    assert info.pages_per_minute_color is None


def test_printer_trays() -> None:
    """Test that input and output trays are parsed onto the Printer."""
    printer = models.Printer.from_dict(
        {
            "printer-input-tray": [
                "type=other;maxcapacity=520;level=130;status=0;name=auto",
                "type=sheetFeedAutoRemovableTray;maxcapacity=520;level=130;name=Tray1",
            ],
            "printer-output-tray": "type=unRemovableBin;maxcapacity=500;name=Finisher",
        },
    )

    assert len(printer.input_trays) == 2
    assert printer.input_trays[1].name == "Tray1"
    assert printer.input_trays[1].level == 130

    assert len(printer.output_trays) == 1
    assert printer.output_trays[0].name == "Finisher"
    assert printer.output_trays[0].max_capacity == 500


def test_printer_without_trays() -> None:
    """Test that a printer reporting no trays yields empty lists.

    A real Samsung M288x reports neither tray attribute.
    """
    printer = models.Printer.from_dict({})

    assert printer.input_trays == []
    assert printer.output_trays == []
    assert printer.status.supported == ()
