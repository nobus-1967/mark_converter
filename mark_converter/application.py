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
    """Application owning the single viewer window and its menu actions."""

    def __init__(self) -> None:
        """Initialize the application with open-file support."""
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self._window = None
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
        window = self._window
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

    def _run_window_action(self, handler: str) -> None:
        """Call a named handler on the viewer window when it exists."""
        if self._window is not None:
            getattr(self._window, handler)()

    def _setup_actions(self) -> None:
        """Create the five actions available in the hamburger menu."""
        actions = {
            "open": "_on_open",
            "convert": "_on_convert",
            "toggle-theme": "_on_toggle_theme",
            "quit": "_on_quit",
            "about": "_on_about",
        }
        for name, handler in actions.items():
            self._add_action(
                name, lambda *_args, handler=handler: self._run_window_action(handler)
            )

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
