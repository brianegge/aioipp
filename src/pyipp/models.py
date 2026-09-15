"""Models for IPP."""

# pylint: disable=R0912,R0915
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from yarl import URL

from .parser import parse_ieee1284_device_id, parse_make_and_model

PRINTER_STATES = {3: "idle", 4: "printing", 5: "stopped"}


def _firmware_version(value: Any) -> str | None:
    """Return a single version string for printer-firmware-string-version.

    The attribute is defined as 1setOf text, so printers with several firmware
    components (Brother, Lexmark, Samsung, Xerox) report a list of versions.
    Join them into one string so consumers always receive ``str | None``.
    """
    if value is None:
        return None

    if isinstance(value, list):
        versions = [str(item) for item in value if item not in (None, "")]
        return ", ".join(versions) if versions else None

    return str(value)


def _as_list(value: Any) -> list[Any]:
    """Return value as a list.

    IPP 1setOf attributes arrive as a bare value when the printer reports a
    single entry, so normalise both shapes to a list.
    """
    if value is None:
        return []

    return value if isinstance(value, list) else [value]


def _parse_keyword_string(value: str) -> dict[str, str]:
    """Parse a PWG "key=value;" string such as printer-input-tray.

    Keys may repeat (Kyocera reports several mediafeed pairs per tray); the
    first occurrence wins, which is the one describing the tray itself.
    """
    parsed: dict[str, str] = {}

    for pair in value.split(";"):
        key, sep, val = pair.partition("=")
        if not sep or not (key := key.strip().lower()):
            continue

        parsed.setdefault(key, val.strip())

    return parsed


def _tray_int(value: str | None) -> int | None:
    """Return a tray level or capacity, or None when out of band.

    PWG 5107.2 uses negative values for out-of-band conditions: -1 other,
    -2 unknown and -3 no limit. None of those are a sheet count.
    """
    if value is None:
        return None

    try:
        number = int(value)
    except ValueError:
        return None

    return number if number >= 0 else None


@dataclass
class Info:
    """Object holding information from IPP."""

    name: str
    printer_name: str
    printer_uri_supported: list[str]
    uptime: int
    command_set: str | None = None
    location: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    printer_info: str | None = None
    serial: str | None = None
    uuid: str | None = None
    version: str | None = None
    more_info: str | None = None
    icons: list[str] = field(default_factory=list)
    pages_per_minute: int | None = None
    pages_per_minute_color: int | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Info:
        """Return Info object from IPP response."""
        cmd = None
        name = "IPP Printer"
        name_parts = []
        serial = None
        _printer_name = printer_name = data.get("printer-name", "")
        make_model = data.get("printer-make-and-model", "")
        device_id = data.get("printer-device-id", "")
        uri_supported = data.get("printer-uri-supported", [])
        uuid = data.get("printer-uuid")

        if not isinstance(uri_supported, list):
            uri_supported = [str(uri_supported)]

        for uri in uri_supported:
            if (URL(uri).path.lstrip("/")) == _printer_name.lstrip("/"):
                _printer_name = ""
                break

        make, model = parse_make_and_model(make_model)
        parsed_device_id = parse_ieee1284_device_id(device_id)

        if parsed_device_id.get("MFG") is not None and len(parsed_device_id["MFG"]) > 0:
            make = parsed_device_id["MFG"]
            name_parts.append(make)

        if parsed_device_id.get("MDL") is not None and len(parsed_device_id["MDL"]) > 0:
            model = parsed_device_id["MDL"]
            name_parts.append(model)

        if parsed_device_id.get("CMD") is not None and len(parsed_device_id["CMD"]) > 0:
            cmd = parsed_device_id["CMD"]

        if len(parsed_device_id.get("SERIALNUMBER") or "") > 0:
            serial = parsed_device_id["SERIALNUMBER"]

        if len(make_model) > 0:
            name = make_model
        elif len(name_parts) == 2:
            name = " ".join(name_parts)
        elif len(_printer_name) > 0:
            name = _printer_name

        return Info(
            command_set=cmd,
            location=data.get("printer-location", ""),
            name=name,
            manufacturer=make,
            model=model,
            printer_name=printer_name,
            printer_info=data.get("printer-info"),
            printer_uri_supported=uri_supported,
            serial=serial,
            uptime=data.get("printer-up-time", 0),
            uuid=uuid[9:] if uuid else None,  # strip urn:uuid: from uuid
            version=_firmware_version(data.get("printer-firmware-string-version")),
            more_info=data.get("printer-more-info"),
            icons=[str(icon) for icon in _as_list(data.get("printer-icons")) if icon],
            pages_per_minute=_int_or_none(data.get("pages-per-minute")),
            pages_per_minute_color=_int_or_none(data.get("pages-per-minute-color")),
        )


@dataclass
class Marker:
    """Object holding marker (ink) info from IPP."""

    marker_id: int
    marker_type: str
    name: str
    color: str
    level: int
    low_level: int
    high_level: int


@dataclass
class Tray:
    """Object holding input or output tray info from IPP.

    ``level`` and ``max_capacity`` are None when the printer reports an
    out-of-band value, so a tray that exists can still report no level.
    """

    name: str | None
    tray_type: str | None
    level: int | None
    max_capacity: int | None
    status: int | None

    @staticmethod
    def from_string(value: str) -> Tray:
        """Return Tray object from a PWG "key=value;" tray string."""
        parsed = _parse_keyword_string(value)

        return Tray(
            name=parsed.get("name") or None,
            tray_type=parsed.get("type") or None,
            level=_tray_int(parsed.get("level")),
            max_capacity=_tray_int(parsed.get("maxcapacity")),
            status=_tray_int(parsed.get("status")),
        )


@dataclass
class Uri:
    """Object holding URI info from IPP."""

    uri: str
    authentication: str | None
    security: str | None


def _int_or_none(value: Any) -> int | None:
    """Return value if it is an integer counter, otherwise None.

    The IPP parser decodes out-of-band values such as unknown or no-value
    as strings, which must not be treated as counter values.
    """
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@dataclass
class Counters:
    """Object holding page counter information from IPP.

    A counter is None when the printer does not report it or reports an
    out-of-band value such as unknown. ``supported`` lists the counters the
    printer reports at all, so a supported counter can still be None.
    """

    impressions_completed: int | None
    impressions_completed_col: dict[str, int | None]
    pages_completed: int | None
    media_sheets_completed: int | None
    supported: tuple[str, ...] = ()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Counters:
        """Return Counters object from IPP response."""
        raw_col = data.get("printer-impressions-completed-col")
        col: dict[str, int | None] = {}
        if isinstance(raw_col, dict):
            col = {name: _int_or_none(value) for name, value in raw_col.items()}

        impressions = _int_or_none(data.get("printer-impressions-completed"))
        if impressions is None and col and None not in col.values():
            # Only a complete collection adds up to the total
            impressions = sum(value for value in col.values() if value is not None)

        supported = []
        if (
            "printer-impressions-completed" in data
            or "printer-impressions-completed-col" in data
        ):
            supported.append("impressions_completed")
        if "printer-pages-completed" in data:
            supported.append("pages_completed")
        if "printer-media-sheets-completed" in data:
            supported.append("media_sheets_completed")

        return Counters(
            impressions_completed=impressions,
            impressions_completed_col=col,
            pages_completed=_int_or_none(data.get("printer-pages-completed")),
            media_sheets_completed=_int_or_none(
                data.get("printer-media-sheets-completed"),
            ),
            supported=tuple(supported),
        )


@dataclass
class Status:
    """Object holding queue and alert information from IPP.

    Follows the same contract as :class:`Counters`: a value is None or empty
    when the printer does not report it, and ``supported`` lists the fields
    the printer reports at all, so a supported field can still be None.
    """

    accepting_jobs: bool | None
    queued_jobs: int | None
    alerts: list[str]
    media_ready: list[str]
    supported: tuple[str, ...] = ()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Status:
        """Return Status object from IPP response."""
        accepting = data.get("printer-is-accepting-jobs")
        if not isinstance(accepting, bool):
            accepting = None

        supported = []
        if accepting is not None:
            supported.append("accepting_jobs")
        if "queued-job-count" in data:
            supported.append("queued_jobs")
        if "printer-alert-description" in data:
            supported.append("alerts")
        if "media-ready" in data:
            supported.append("media_ready")

        return Status(
            accepting_jobs=accepting,
            queued_jobs=_int_or_none(data.get("queued-job-count")),
            alerts=[
                str(alert)
                for alert in _as_list(data.get("printer-alert-description"))
                if alert not in (None, "")
            ],
            media_ready=[
                str(media)
                for media in _as_list(data.get("media-ready"))
                if media not in (None, "")
            ],
            supported=tuple(supported),
        )


@dataclass
class State:
    """Object holding the IPP printer state."""

    printer_state: str
    reasons: str | None
    message: str | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> State:
        """Return State object from IPP response."""
        state = data.get("printer-state", 0)

        if (reasons := data.get("printer-state-reasons")) == "none":
            reasons = None

        return State(
            printer_state=PRINTER_STATES.get(state, state),
            reasons=reasons,
            message=data.get("printer-state-message"),
        )


@dataclass
class Printer:
    """Object holding the IPP printer information."""

    info: Info
    counters: Counters
    markers: list[Marker]
    state: State
    status: Status
    input_trays: list[Tray]
    output_trays: list[Tray]
    uris: list[Uri]
    booted_at: datetime

    def as_dict(self) -> dict[str, Any]:
        """Return dictionary version of this printer."""
        return {
            "info": asdict(self.info),
            "counters": asdict(self.counters),
            "state": asdict(self.state),
            "status": asdict(self.status),
            "markers": [asdict(marker) for marker in self.markers],
            "input_trays": [asdict(tray) for tray in self.input_trays],
            "output_trays": [asdict(tray) for tray in self.output_trays],
            "uris": [asdict(uri) for uri in self.uris],
            "booted_at": self.booted_at,
        }

    def update_from_dict(self, data: dict[str, Any]) -> Printer:
        """Return updated Printer object from IPP response data."""
        last_uptime = self.info.uptime

        self.info = Info.from_dict(data)
        self.counters = Counters.from_dict(data)
        self.markers = Printer.merge_marker_data(data)
        self.state = State.from_dict(data)
        self.status = Status.from_dict(data)
        self.input_trays = Printer.parse_trays(data, "printer-input-tray")
        self.output_trays = Printer.parse_trays(data, "printer-output-tray")
        self.uris = Printer.merge_uri_data(data)

        if self.info.uptime < last_uptime:
            self.booted_at = _utcnow() - timedelta(seconds=self.info.uptime)

        return self

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Printer:
        """Return Printer object from IPP response data."""
        info = Info.from_dict(data)

        return Printer(
            info=info,
            counters=Counters.from_dict(data),
            markers=Printer.merge_marker_data(data),
            state=State.from_dict(data),
            status=Status.from_dict(data),
            input_trays=Printer.parse_trays(data, "printer-input-tray"),
            output_trays=Printer.parse_trays(data, "printer-output-tray"),
            uris=Printer.merge_uri_data(data),
            booted_at=(_utcnow() - timedelta(seconds=info.uptime)),
        )

    @staticmethod
    def parse_trays(data: dict[str, Any], attribute: str) -> list[Tray]:
        """Return the trays reported under the given attribute."""
        return [
            Tray.from_string(str(value))
            for value in _as_list(data.get(attribute))
            if value not in (None, "")
        ]

    @staticmethod
    def merge_marker_data(  # noqa: PLR0912, C901
        data: dict[str, Any],
    ) -> list[Marker]:
        """Return Marker data from IPP response."""
        marker_names = []
        marker_colors = []
        marker_levels = []
        marker_types = []
        marker_highs = []
        marker_lows = []

        if not data.get("marker-names"):
            return []

        if isinstance(data["marker-names"], list):
            marker_names = data["marker-names"]
        elif isinstance(data["marker-names"], str):
            marker_names = [data["marker-names"]]

        if not (mlen := len(marker_names)):
            return []

        for _ in range(mlen):
            marker_colors.append("")
            marker_levels.append(-2)
            marker_types.append("unknown")
            marker_highs.append(100)
            marker_lows.append(0)

        if isinstance(data.get("marker-colors"), list):
            for index, list_value in enumerate(data["marker-colors"]):
                if index < mlen:
                    marker_colors[index] = list_value
        elif isinstance(data.get("marker-colors"), str) and mlen == 1:
            marker_colors[0] = data["marker-colors"]

        if isinstance(data.get("marker-levels"), list):
            for index, list_value in enumerate(data["marker-levels"]):
                if index < mlen:
                    marker_levels[index] = list_value
        elif isinstance(data.get("marker-levels"), int) and mlen == 1:
            marker_levels[0] = data["marker-levels"]

        if isinstance(data.get("marker-high-levels"), list):
            for index, list_value in enumerate(data["marker-high-levels"]):
                if index < mlen:
                    marker_highs[index] = list_value
        elif isinstance(data.get("marker-high-levels"), int) and mlen == 1:
            marker_highs[0] = data["marker-high-levels"]

        if isinstance(data.get("marker-low-levels"), list):
            for index, list_value in enumerate(data["marker-low-levels"]):
                if index < mlen:
                    marker_lows[index] = list_value
        elif isinstance(data.get("marker-low-levels"), int) and mlen == 1:
            marker_lows[0] = data["marker-low-levels"]

        if isinstance(data.get("marker-types"), list):
            for index, list_value in enumerate(data["marker-types"]):
                if index < mlen:
                    marker_types[index] = list_value
        elif isinstance(data.get("marker-types"), str) and mlen == 1:
            marker_types[0] = data["marker-types"]

        markers = [
            Marker(
                marker_id=marker_id,
                marker_type=marker_types[marker_id],
                name=marker_names[marker_id],
                color=marker_colors[marker_id],
                level=marker_levels[marker_id],
                high_level=marker_highs[marker_id],
                low_level=marker_lows[marker_id],
            )
            for marker_id in range(mlen)
        ]
        markers.sort(key=lambda x: x.name)

        return markers

    @staticmethod
    def merge_uri_data(data: dict[str, Any]) -> list[Uri]:  # noqa: PLR0912
        """Return URI data from IPP response."""
        _uris: list[str] = []
        auth: list[str | None] = []
        security: list[str | None] = []

        if not data.get("printer-uri-supported"):
            return []

        if isinstance(data["printer-uri-supported"], list):
            _uris = data["printer-uri-supported"]
        elif isinstance(data["printer-uri-supported"], str):
            _uris = [data["printer-uri-supported"]]

        if not (ulen := len(_uris)):
            return []

        for _ in range(ulen):
            auth.append(None)
            security.append(None)

        if isinstance(data.get("uri-authentication-supported"), list):
            for k, list_value in enumerate(data["uri-authentication-supported"]):
                if k < ulen:
                    auth[k] = _str_or_none(list_value)
        elif isinstance(data.get("uri-authentication-supported"), str) and ulen == 1:
            auth[0] = _str_or_none(data["uri-authentication-supported"])

        if isinstance(data.get("uri-security-supported"), list):
            for k, list_value in enumerate(data["uri-security-supported"]):
                if k < ulen:
                    security[k] = _str_or_none(list_value)
        elif isinstance(data.get("uri-security-supported"), str) and ulen == 1:
            security[0] = _str_or_none(data["uri-security-supported"])

        return [
            Uri(
                uri=_uris[uri_id],
                authentication=auth[uri_id],
                security=security[uri_id],
            )
            for uri_id in range(ulen)
        ]


def _utcnow() -> datetime:
    """Return the current date and time in UTC."""
    return datetime.now(tz=UTC)


def _str_or_none(value: str) -> str | None:
    """Return string while handling string representations of None."""
    if value == "none":
        return None

    return value
