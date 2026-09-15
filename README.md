# Python: Internet Printing Protocol (IPP) Client

Asynchronous Python client for Internet Printing Protocol (IPP).

> **Note:** `aioipp` is a maintained fork of [pyipp](https://github.com/ctalkington/python-ipp)
> by Chris Talkington. It keeps the `pyipp` import name and adds page counter support.
> It is published on PyPI as `aioipp`; do not install it alongside `pyipp`.

## About

This package allows you to monitor printers that support the Internet Printing Protocol (IPP) programmatically.

## Installation

```bash
pip install aioipp
```

## Usage

```python
import asyncio

from pyipp import IPP, Printer


async def main():
    """Show example of connecting to your IPP print server."""
    async with IPP("ipps://EPSON123456.local:631/ipp/print") as ipp:
        printer: Printer = await ipp.printer()
        print(printer)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```

## Reporting a problem with your printer

Printers vary a lot in how closely they follow the IPP specification. If your
printer fails to set up in Home Assistant, or a value looks wrong, the most
useful thing you can provide is a raw capture of what the printer sends. The
package ships a small diagnostics command for exactly that:

```bash
pipx run aioipp ipp://192.168.1.10:631/ipp/print
```

or, in an environment where the package is already installed:

```bash
python -m pyipp ipp://192.168.1.10:631/ipp/print
```

Use `ipps://` if the printer requires TLS, and `--ipp-version 1.1` for older
devices. The command prints the attributes the library received, what it parsed
them into, and a full traceback if parsing failed. It always writes the raw
response to `ipp-<host>.bin` in the current directory.

Then [open an issue](https://github.com/brianegge/aioipp/issues/new?template=bug_report.yml)
with:

- the printer make, model and firmware version
- the full output of the command
- the `ipp-<host>.bin` file (zip it if GitHub refuses the extension)

The capture may contain the printer's serial number and UUID. Remove them if
you consider them private. Captured files become regression tests in
`tests/fixtures`, so they are the fastest route to a fix.

If you cannot install Python packages, the `ipptool` command that ships with
CUPS on Linux and macOS is a good substitute:

```bash
ipptool -tv ipp://192.168.1.10:631/ipp/print get-printer-attributes.test
```

## Setting up development environment

This Python project is fully managed using the [Poetry](https://python-poetry.org) dependency
manager. But also relies on the use of NodeJS for certain checks during
development.

You need at least:

- Python 3.9+
- [Poetry](https://python-poetry.org/docs/#installation)
- NodeJS 20+ (including NPM)

To install all packages, including all development requirements:

```bash
npm install
poetry install
```

As this repository uses the [pre-commit](https://pre-commit.com/) framework, all changes
are linted and tested with each commit. You can run all checks and tests
manually, using the following command:

```bash
poetry run pre-commit run --all-files
```

To run just the Python tests:

```bash
poetry run pytest
```
