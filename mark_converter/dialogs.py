"""Dialogs used by Mark Converter (GTK4 / libadwaita)."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


def _make_dialog_box(spacing: int = 8) -> Gtk.Box:
    """Create a vertical dialog content box with standard margins."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    box.set_margin_top(24)
    box.set_margin_bottom(24)
    box.set_margin_start(24)
    box.set_margin_end(24)
    return box


def _make_button(
    label: str, callback: Callable[[Gtk.Button], None], *, suggested: bool = False
) -> Gtk.Button:
    """Create a button connected to *callback* with an optional suggested style."""
    btn = Gtk.Button(label=label)
    if suggested:
        btn.add_css_class("suggested-action")
    btn.connect("clicked", callback)
    return btn


def _make_button_box(*buttons: Gtk.Button) -> Gtk.Box:
    """Create a horizontally centered box containing the given buttons."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.set_halign(Gtk.Align.CENTER)
    box.set_margin_top(12)
    for btn in buttons:
        box.append(btn)
    return box


def show_message(
    parent: Gtk.Window, title: str, message: str, icon: str = "info"
) -> None:
    """Display an alert dialog with an *icon* role (info, warning or error)."""
    alert = Adw.AlertDialog()
    alert.set_heading(title)
    alert.set_body(message)
    alert.add_response("ok", "_OK")
    if icon == "error":
        alert.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
    elif icon == "warning":
        alert.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
    alert.present(parent)


class ChoiceDialog(Adw.Dialog):
    """Dialog for selecting an item from a drop-down list."""

    def __init__(self, prompt: str, items: list[str], initial: str) -> None:
        """Initialize the Choice dialog with prompt, items and initial selection."""
        super().__init__()
        self.set_title("Select")
        self.set_content_width(380)

        self.result: str | None = None

        box = _make_dialog_box(spacing=12)

        lbl = Gtk.Label(label=prompt)
        lbl.set_xalign(0.0)
        box.append(lbl)

        self._dropdown = Gtk.DropDown()
        model = Gtk.StringList()
        for item in items:
            model.append(item)
        self._dropdown.set_model(model)
        idx = items.index(initial) if initial in items else 0
        self._dropdown.set_selected(idx)
        box.append(self._dropdown)

        ok_btn = _make_button("OK", self._on_ok, suggested=True)
        cancel_btn = _make_button("Cancel", lambda _: self.close())
        box.append(_make_button_box(ok_btn, cancel_btn))
        self.set_child(box)

    def _on_ok(self, *_args) -> None:
        """Store the selected item and close the dialog."""
        model = self._dropdown.get_model()
        idx = self._dropdown.get_selected()
        if idx is not None and idx < model.get_n_items():
            self.result = model.get_string(idx)
        self.close()


class AboutDialog(Adw.Dialog):
    """Dialog showing application name, version and release information."""

    def __init__(self, app_name: str, version: str, release: str) -> None:
        """Initialize the About dialog with app name, version and release."""
        super().__init__()
        self.set_title("About")
        self.set_content_width(360)

        box = _make_dialog_box(spacing=12)
        box.set_halign(Gtk.Align.CENTER)

        lbl = Gtk.Label(label=f"{app_name}, version {version} ({release})")
        box.append(lbl)

        close_btn = _make_button("Close", lambda _: self.close())
        close_btn.set_size_request(100, -1)
        box.append(close_btn)

        self.set_child(box)
