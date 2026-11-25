"""WebKitGTK widget that renders Markdown as styled HTML5."""

from __future__ import annotations

import contextlib
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, WebKit

from mark_converter.constants import WELCOME_MD
from mark_converter.helpers import render_temp_html


class MarkdownViewer(Gtk.Box):
    """A WebKit view backed by a temporary HTML5 file.

    Markdown is converted with markdown2html5-base and written to a temp file
    before it is loaded, so relative image links from the source document keep
    working. The temp file is replaced on every render and removed on close.
    """

    def __init__(self) -> None:
        """Create an empty viewer with file access enabled for local assets."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._html_path: Path | None = None
        self._web_view = WebKit.WebView()
        self._web_view.set_hexpand(True)
        self._web_view.set_vexpand(True)

        settings = self._web_view.get_settings()
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_allow_file_access_from_file_urls(True)

        self.append(self._web_view)

    def display(
        self,
        markdown: str,
        source_file: Path | None,
        *,
        page_layout: str = "portrait",
    ) -> None:
        """Convert *markdown* to HTML5 and show the resulting temp file."""
        self.clear_temp()
        self._html_path = render_temp_html(
            markdown, source_file, page_layout=page_layout
        )
        self._web_view.load_uri(self._html_path.as_uri())

    def display_welcome(self) -> None:
        """Show the startup page (itself rendered from Markdown)."""
        self.display(WELCOME_MD, None)

    def clear_temp(self) -> None:
        """Delete the temporary HTML file if one is currently in use."""
        if self._html_path is not None:
            with contextlib.suppress(OSError):
                self._html_path.unlink(missing_ok=True)
            self._html_path = None

    @property
    def html_path(self) -> Path | None:
        """Return the path of the temp HTML file currently being displayed."""
        return self._html_path
