"""Main Mark Converter window (GTK4).

A minimal viewer: a header bar with the hamburger menu and a WebKit view that
renders Markdown as HTML5. There is deliberately no menu bar and no editor.
Document lifecycle and Convert... follow Mark Editor 1.1.0.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk

from mark_converter.constants import APP_NAME, CONVERT_FORMATS, RELEASE, VERSION
from mark_converter.dialogs import AboutDialog, ChoiceDialog, show_message
from mark_converter.helpers import (
    THEMES,
    load_theme,
    md_to_html,
    md_to_pdf,
    md_to_plain,
    save_theme,
)
from mark_converter.viewer import MarkdownViewer


def _make_md_filters() -> Gio.ListStore:
    """Return a ListStore of file filters (Markdown docs and all files)."""
    md_filter = Gtk.FileFilter()
    md_filter.set_name("Markdown files")
    md_filter.add_pattern("*.md")
    md_filter.add_pattern("*.markdown")
    all_filter = Gtk.FileFilter()
    all_filter.set_name("All files")
    all_filter.add_pattern("*")
    store = Gio.ListStore.new(Gtk.FileFilter)
    store.append(md_filter)
    store.append(all_filter)
    return store


def conversion_settings(choice: str) -> tuple[str, str]:
    """Map a Convert... format choice to ``(extension, page_layout)``."""
    if choice.startswith("HTML5"):
        ext = ".html"
    elif choice.startswith("Plain"):
        ext = ".txt"
    else:
        ext = ".pdf"
    page_layout = "landscape" if "landscape" in choice else "portrait"
    return ext, page_layout


MENU_SECTIONS: tuple[tuple[tuple[str, str, str], ...], ...] = (
    (
        ("Open...", "app.open", "<Control>o"),
        ("Convert...", "app.convert", "<Control>e"),
    ),
    (
        ("Toggle Theme", "app.toggle-theme", "<Control><Alt>g"),
        ("Quit", "app.quit", "<Control>q"),
    ),
    (("About", "app.about", ""),),
)


def _add_menu_item(menu: Gio.Menu, label: str, action: str, accel: str) -> None:
    """Append a menu item with its keyboard accelerator shown in the popover."""
    item = Gio.MenuItem.new(label, action)
    if accel:
        item.set_attribute_value("accel", GLib.Variant("s", accel))
    menu.append_item(item)


class MarkConverterWindow(Gtk.ApplicationWindow):
    """The single Markdown viewer window."""

    def __init__(self, **kwargs) -> None:
        """Initialize the viewer window and show the startup page."""
        super().__init__(**kwargs)
        self.set_title(APP_NAME)
        self.set_default_size(1100, 700)
        self.set_size_request(600, 400)

        self.current_file: Path | None = None
        self._markdown = ""
        self._theme_mode = load_theme()

        self._build_ui()
        self._viewer.display_welcome()
        self._update_title()
        self.connect("close-request", self._on_close_request)

    def _build_ui(self) -> None:
        """Assemble the header bar (burger menu only) and the viewer."""
        header = Gtk.HeaderBar()
        menu_btn = Gtk.MenuButton()
        menu_btn.set_menu_model(self._build_menu_model())
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Menu")
        header.pack_end(menu_btn)
        self.set_titlebar(header)

        self._viewer = MarkdownViewer()
        self._viewer.set_vexpand(True)
        self._viewer.set_hexpand(True)
        self.set_child(self._viewer)

    def _build_menu_model(self) -> Gio.Menu:
        """Return the only menu: the hamburger menu with five commands."""
        menu = Gio.Menu()
        for section_items in MENU_SECTIONS:
            section = Gio.Menu()
            for label, action, accel in section_items:
                _add_menu_item(section, label, action, accel)
            menu.append_section(None, section)
        return menu

    def _update_title(self) -> None:
        """Refresh the title with the name of the currently viewed file."""
        name = self.current_file.name if self.current_file else "No file"
        self.set_title(f"{APP_NAME} — {name}")

    def _on_open(self) -> None:
        """Open a file chooser to select a Markdown document."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Markdown file")
        dialog.set_filters(_make_md_filters())
        dialog.open(self, None, self._on_open_response)

    def _on_open_response(self, dialog, result) -> None:
        """Handle the result of the Open file dialog."""
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        self.load_file(Path(file.get_path()))

    def load_file(self, path: Path) -> None:
        """Read *path* as Markdown and render it in the viewer."""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            show_message(self, "Open file", str(exc), "error")
            return
        try:
            self._viewer.display(text, path)
        except Exception as exc:
            show_message(self, "Open file", str(exc), "error")
            return
        self._markdown = text
        self.current_file = path
        self._update_title()

    def _on_convert(self) -> None:
        """Show the format chooser, then a file dialog for export."""
        formats = list(CONVERT_FORMATS)
        dlg = ChoiceDialog(
            prompt="Choose the target format:", items=formats, initial=formats[0]
        )
        dlg.connect("closed", lambda _: self._convert_after_choice(dlg.result))
        dlg.present()

    def _convert_after_choice(self, choice: str | None) -> None:
        """Show the file-save dialog after the user picks an export format."""
        if not choice:
            return
        ext, page_layout = conversion_settings(choice)

        f = Gtk.FileFilter()
        f.set_name(
            f"{'HTML5' if ext == '.html' else 'Text' if ext == '.txt' else 'PDF'} files"
        )
        f.add_pattern(f"*{ext}")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)

        base = self.current_file.name if self.current_file else "document"
        if base.endswith((".md", ".markdown")):
            base = base.rsplit(".", 1)[0]

        dialog = Gtk.FileDialog()
        dialog.set_title("Convert")
        dialog.set_initial_name(base + ext)
        dialog.set_filters(filters)
        dialog.save(
            self,
            None,
            lambda d, r: self._perform_convert_response(d, r, ext, page_layout),
        )

    def _perform_convert_response(
        self, dialog, result, ext: str, page_layout: str = "portrait"
    ) -> None:
        """Handle the result of the Convert file dialog and perform the export."""
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        path = Path(file.get_path())
        try:
            content = self._markdown
            if ext == ".html":
                html = md_to_html(content, page_layout=page_layout)
                path.write_text(html, encoding="utf-8")
            elif ext == ".txt":
                path.write_text(md_to_plain(content), encoding="utf-8")
            else:
                md_to_pdf(
                    content,
                    str(path),
                    source_file=self.current_file,
                    page_layout=page_layout,
                )
        except Exception as exc:
            show_message(self, "Convert", str(exc), "error")
            return
        show_message(self, "Convert", "Conversion complete!")

    def _on_toggle_theme(self) -> None:
        """Switch between light and dark appearance modes and persist the choice."""
        new = "dark" if self._theme_mode == "light" else "light"
        self._apply_theme(new)

    def _apply_theme(self, name: str) -> None:
        """Apply the named theme (``light`` or ``dark``) and save it."""
        name = name.lower()
        if name not in THEMES:
            return
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", name == "dark")
        self._theme_mode = name
        save_theme(name)

    def _on_about(self) -> None:
        """Show the About dialog with version 0.1.0 (2026.11)."""
        AboutDialog(APP_NAME, VERSION, RELEASE).present()

    def _on_quit(self) -> None:
        """Clean up and close the application window."""
        self.close()

    def _on_close_request(self, _widget) -> bool:
        """Delete the temporary HTML file when the viewer closes."""
        self._viewer.clear_temp()
        return False
