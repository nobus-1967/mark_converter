"""Mark Converter -- entry point."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib


def main() -> None:
    """Suppress harmless GTK4 layout warnings, then launch the app."""

    def _log_handler(domain, level, message, user_data):
        """Ignore harmless initial-rendering warnings."""
        if "snapshot" in message.lower() or "allocation" in message.lower():
            return
        GLib.log_default_handler(domain, level, message, user_data)

    GLib.log_set_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING, _log_handler, None)

    from mark_converter.application import MarkConverterApp

    app = MarkConverterApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
