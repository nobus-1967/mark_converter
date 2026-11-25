"""Gtk.Application subclass for Mark Converter: actions and shortcuts."""

from __future__ import annotations

import contextlib
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gio, Gtk

from mark_converter.constants import APP_ID
from mark_converter.helpers import load_theme


class MarkConverterApp(Gtk.Application):
    """Application owning the single viewer window and its four commands."""

    def __init__(self) -> None:
        """Initialize the application with open-file support."""
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.connect("activate", self._on_activate)
        self.connect("startup", self._on_startup)
        self.connect("open", self._on_open_files)

    def _on_startup(self, _app) -> None:
        """Register actions and keyboard shortcuts once at startup."""
        self._setup_actions()
        self._setup_shortcuts()

    def _on_activate(self, app) -> None:
        """Apply the saved theme and present the viewer window."""
        settings = Gtk.Settings.get_default()
        settings.set_property(
            "gtk-application-prefer-dark-theme", load_theme() == "dark"
        )

        from mark_converter.window import MarkConverterWindow

        self._window = MarkConverterWindow(application=app)
        self._window.present()

    def _on_open_files(self, _app, files, _n_files, _hint) -> None:
        """Load the first Markdown file passed on the command line."""
        window = getattr(self, "_window", None)
        if window is None:
            self._on_activate(self)
            window = self._window
        if window and files:
            path = files[0].get_path()
            if path:
                window.load_file(Path(path))

    def _add_action(self, name: str, callback) -> None:
        """Register a stateless ``Gio.SimpleAction`` on this application."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def _setup_actions(self) -> None:
        """Create the only actions available in the hamburger menu."""

        def _w():
            """Return the current viewer window."""
            return getattr(self, "_window", None)

        self._add_action("open", lambda a, p: _w() and _w()._on_open())
        self._add_action("convert", lambda a, p: _w() and _w()._on_convert())
        self._add_action("toggle-theme", lambda a, p: _w() and _w()._on_toggle_theme())
        self._add_action("quit", lambda a, p: _w() and _w()._on_quit())
        self._add_action("about", lambda a, p: _w() and _w()._on_about())

    def _setup_shortcuts(self) -> None:
        """Bind the four keyboard shortcuts kept from the editor."""
        shortcuts = {
            "app.open": ["<Control>o"],
            "app.convert": ["<Control>e"],
            "app.toggle-theme": ["<Control><Alt>g"],
            "app.quit": ["<Control>q"],
        }
        for action_name, accels in shortcuts.items():
            with contextlib.suppress(Exception):
                self.set_accels_for_action(action_name, accels)
