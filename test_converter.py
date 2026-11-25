#!/usr/bin/env python3
"""Tests for Mark Converter 0.1.0 (GTK4 / WebKitGTK)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mark_converter.constants import (  # noqa: E402
    APP_ID,
    APP_NAME,
    CONVERT_FORMATS,
    DEFAULT_THEME,
    RELEASE,
    THEMES,
    VERSION,
)
from mark_converter.helpers import (  # noqa: E402
    get_temp_html_path,
    md_to_html,
    md_to_plain,
    render_temp_html,
)
from mark_converter.window import (  # noqa: E402
    MENU_SECTIONS,
    conversion_settings,
)


class _IsolatedConfigMixin:
    """Point Mark Converter's config and cache dirs at a temporary directory."""

    def setUp(self):
        """Redirect config and cache dirs to a fresh temporary directory."""
        import mark_converter.helpers as mh

        self._orig = (mh.CONFIG_DIR, mh.THEME_FILE, mh.CACHE_DIR)
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        mh.CONFIG_DIR = root / ".config"
        mh.THEME_FILE = mh.CONFIG_DIR / "theme.json"
        mh.CACHE_DIR = root / ".cache"

    def tearDown(self):
        """Restore the original config and cache dirs."""
        import mark_converter.helpers as mh

        mh.CONFIG_DIR, mh.THEME_FILE, mh.CACHE_DIR = self._orig
        self._tmp.cleanup()


class TestAppMetadata(unittest.TestCase):
    """Check static application metadata."""

    def test_identity(self):
        """Name, id, version and release describe Mark Converter 0.1.0."""
        self.assertEqual(APP_NAME, "Mark Converter")
        self.assertEqual(APP_ID, "com.github.mark_converter")
        self.assertEqual(VERSION, "0.1.0")
        self.assertEqual(RELEASE, "2026.11")

    def test_themes(self):
        """Light and dark themes are available, light is the default."""
        self.assertEqual(THEMES, ("light", "dark"))
        self.assertEqual(DEFAULT_THEME, "light")


class TestThemeStorage(_IsolatedConfigMixin, unittest.TestCase):
    """Verify theme persistence in ~/.config/mark_converter."""

    def test_round_trip(self):
        """A saved theme is restored on the next load."""
        from mark_converter.helpers import load_theme, save_theme

        self.assertEqual(load_theme(), DEFAULT_THEME)
        save_theme("dark")
        self.assertEqual(load_theme(), "dark")

    def test_invalid_value_falls_back(self):
        """Unknown saved modes fall back to the default."""
        from mark_converter.helpers import load_theme, save_theme

        save_theme("blue")
        self.assertEqual(load_theme(), DEFAULT_THEME)


class TestTempHtml(_IsolatedConfigMixin, unittest.TestCase):
    """Verify temporary HTML files live in the configured cache/folder."""

    def test_path_without_file(self):
        """Without an opened file, Temp.html goes into the cache dir."""
        import mark_converter.helpers as mh

        expected = mh.CACHE_DIR / "Temp.html"
        self.assertEqual(get_temp_html_path(None), expected)

    def test_path_beside_source(self):
        """With an opened file, the temp HTML uses the ~<stem>.html name."""
        source = Path(tempfile.gettempdir()) / "notes.md"
        self.assertEqual(get_temp_html_path(source), source.parent / "~notes.html")

    def test_render_temp_html(self):
        """Rendering writes a full HTML5 document into the temp file."""
        import mark_converter.helpers as mh

        path = render_temp_html("# Hello\n\n**world**", None)
        self.assertEqual(path, mh.CACHE_DIR / "Temp.html")
        html = path.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", html)
        self.assertIn("<h1", html)
        self.assertIn("Hello", html)

    def test_render_beside_source(self):
        """The rendered temp file is created beside the source document."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "chapter.md"
            source.write_text("# Chapter", encoding="utf-8")
            path = render_temp_html(source.read_text(encoding="utf-8"), source)
            self.assertEqual(path, source.parent / "~chapter.html")
            self.assertTrue(path.exists())


class TestConversion(unittest.TestCase):
    """Verify markdown2html5-base conversion and the Convert... mapping."""

    def test_html_conversion(self):
        """Markdown becomes a styled HTML5 document."""
        html = md_to_html("# Title\n\nText with **bold**.")
        self.assertIn("<!doctype html>", html)
        self.assertIn("<style>", html)
        self.assertIn("Title", html)
        self.assertIn("<strong>bold</strong>", html)

    def test_landscape_layout(self):
        """Landscape conversion can be requested via page_layout."""
        portrait = md_to_html("text", page_layout="portrait")
        landscape = md_to_html("text", page_layout="landscape")
        self.assertNotEqual(portrait, landscape)

    def test_plain_conversion(self):
        """Plain-text export strips heading and emphasis markers."""
        self.assertEqual(md_to_plain("# Title\n\n**bold**"), "Title\n\nbold\n")

    def test_pdf_conversion(self):
        """PDF export prints through headless Chromium and removes its HTML."""
        if shutil.which("chromium") is None:
            self.skipTest("chromium is not installed")
        from mark_converter.helpers import md_to_pdf

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "doc.md"
            source.write_text("# PDF\n\nHello", encoding="utf-8")
            out = Path(folder) / "doc.pdf"
            md_to_pdf(source.read_text(encoding="utf-8"), str(out), source_file=source)
            self.assertTrue(out.exists())
            self.assertTrue(out.read_bytes().startswith(b"%PDF"))
            self.assertFalse((Path(folder) / "doc.html").exists())

    def test_convert_formats(self):
        """HTML5 landscape is removed; PDF landscape remains."""
        self.assertEqual(
            list(CONVERT_FORMATS),
            [
                "HTML5 file (.html)",
                "Plain text file (.txt)",
                "PDF file portrait (.pdf)",
                "PDF file landscape (.pdf)",
            ],
        )

    def test_conversion_settings(self):
        """Each choice maps to the right extension and page layout."""
        expected = [
            (".html", "portrait"),
            (".txt", "portrait"),
            (".pdf", "portrait"),
            (".pdf", "landscape"),
        ]
        self.assertEqual(
            [conversion_settings(choice) for choice in CONVERT_FORMATS], expected
        )


class TestMenuModel(unittest.TestCase):
    """Check that the only menu contains exactly the five required commands."""

    def test_menu_sections(self):
        """Open, Convert, Toggle Theme, Quit and About are the whole menu."""
        self.assertEqual(
            tuple(item[:2] for section in MENU_SECTIONS for item in section),
            (
                ("Open...", "app.open"),
                ("Convert...", "app.convert"),
                ("Toggle Theme", "app.toggle-theme"),
                ("Quit", "app.quit"),
                ("About", "app.about"),
            ),
        )

    def test_shortcuts(self):
        """The four editor shortcuts are registered on the application."""
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        app = Gtk.Application(application_id=f"{APP_ID}.test.shortcuts")
        app.register()
        try:
            from mark_converter.application import MarkConverterApp

            converter_app = MarkConverterApp()
            converter_app.register()
            self.assertEqual(
                converter_app.get_accels_for_action("app.open"), ["<Control>o"]
            )
            self.assertEqual(
                converter_app.get_accels_for_action("app.convert"), ["<Control>e"]
            )
            self.assertEqual(
                converter_app.get_accels_for_action("app.toggle-theme"),
                ["<Control><Alt>g"],
            )
            self.assertEqual(
                converter_app.get_accels_for_action("app.quit"), ["<Control>q"]
            )
            converter_app.quit()
        finally:
            app.quit()


class _GtkTestCase(_IsolatedConfigMixin, unittest.TestCase):
    """Base class that creates a real GTK4 viewer window when a display exists."""

    def setUp(self):
        """Create an isolated application and viewer window, or skip."""
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        super().setUp()
        try:
            self._app = Gtk.Application(
                application_id=f"{APP_ID}.test.{self.id().replace('.', '_')}"
            )
            self._app.register()
            from mark_converter.window import MarkConverterWindow

            self.window = MarkConverterWindow(application=self._app)
        except Exception as exc:
            self.skipTest(f"GTK4 display not available: {exc}")

    def tearDown(self):
        """Remove the temp file and close the window."""
        if hasattr(self, "window"):
            self.window._viewer.clear_temp()
            self.window.close()
        if hasattr(self, "_app"):
            self._app.quit()
        super().tearDown()

    @staticmethod
    def _labels(widget):
        """Collect the text of every Gtk.Label inside *widget*."""
        from gi.repository import Gtk

        labels: list[str] = []
        if hasattr(widget, "get_child"):
            widget = widget.get_child()
        stack = [widget]
        while stack:
            current = stack.pop()
            if current is None:
                continue
            if isinstance(current, Gtk.Label):
                labels.append(current.get_text())
            child = current.get_first_child()
            while child is not None:
                stack.append(child)
                child = child.get_next_sibling()
        return labels


class TestViewerWindow(_GtkTestCase):
    """Behavioral tests for the real viewer window."""

    def test_no_menu_bar(self):
        """The window has a hamburger menu button but no menu bar or editor."""
        from gi.repository import Gtk

        self.assertFalse(hasattr(self.window, "_menubar"))
        self.assertFalse(hasattr(self.window, "_editor"))
        self.assertNotIsInstance(self.window.get_child(), Gtk.PopoverMenuBar)
        self.assertEqual(self.window.get_title(), f"{APP_NAME} — No file")

    def test_welcome_page_is_html(self):
        """The startup page is rendered from Markdown to a temp HTML file."""
        path = self.window._viewer.html_path
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertIn("Mark Converter", path.read_text(encoding="utf-8"))

    def test_load_file(self):
        """Opening a Markdown file renders it and updates the window title."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "article.md"
            source.write_text("# Article\n\nSome **text**.", encoding="utf-8")
            self.window.load_file(source)
            path = self.window._viewer.html_path
            self.assertEqual(path, source.parent / "~article.html")
            html = path.read_text(encoding="utf-8")
            self.assertIn("Article", html)
            self.assertIn("<strong>text</strong>", html)
            self.assertEqual(self.window.get_title(), f"{APP_NAME} — article.md")

    def test_export_html_and_text(self):
        """Convert... writes HTML5 and plain text using the loaded Markdown."""
        from gi.repository import Gio

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "article.md"
            source.write_text("# Article\n\nSome **text**.", encoding="utf-8")
            self.window.load_file(source)

            class _FakeDialog:
                """Minimal dialog returning a fixed destination file."""

                def __init__(self, path: Path):
                    """Store the destination file for the fake dialog."""
                    self.file = Gio.File.new_for_path(str(path))

                def save_finish(self, _result):
                    """Return the destination as a Gio.File."""
                    return self.file

            html_out = Path(folder) / "article.html"
            with mock.patch("mark_converter.window.show_message"):
                self.window._perform_convert_response(
                    _FakeDialog(html_out), None, ".html", "portrait"
                )
            self.assertIn("Article", html_out.read_text(encoding="utf-8"))
            self.assertIn("<!doctype html>", html_out.read_text(encoding="utf-8"))

            txt_out = Path(folder) / "article.txt"
            with mock.patch("mark_converter.window.show_message"):
                self.window._perform_convert_response(
                    _FakeDialog(txt_out), None, ".txt", "portrait"
                )
            self.assertEqual(
                txt_out.read_text(encoding="utf-8"), "Article\n\nSome text.\n"
            )

    def test_toggle_theme(self):
        """Toggle Theme switches and persists the appearance mode."""
        from gi.repository import Gtk

        from mark_converter.helpers import load_theme

        self.assertEqual(load_theme(), "light")
        self.window._on_toggle_theme()
        self.assertEqual(load_theme(), "dark")
        self.assertTrue(
            Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme")
        )

    def test_about_version(self):
        """The About dialog shows version 0.1.0 (2026.11)."""
        from mark_converter.dialogs import AboutDialog

        dlg = AboutDialog(APP_NAME, VERSION, RELEASE)
        text = " ".join(self._labels(dlg))
        self.assertIn("Mark Converter", text)
        self.assertIn("version 0.1.0 (2026.11)", text)


if __name__ == "__main__":
    unittest.main()
