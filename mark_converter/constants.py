"""Application constants for Mark Converter."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "Mark Converter"
APP_ID = "com.github.mark_converter"
VERSION = "0.1.0"
RELEASE = "2026.11"

CONFIG_DIR = Path.home() / ".config" / "mark_converter"
THEME_FILE = CONFIG_DIR / "theme.json"

CACHE_DIR = Path.home() / ".cache" / "mark_converter"
TEMP_HTML = "Temp.html"

THEMES: tuple[str, ...] = ("light", "dark")
DEFAULT_THEME = "light"

CONVERT_FORMATS: tuple[str, ...] = (
    "HTML5 file (.html)",
    "Plain text file (.txt)",
    "PDF file portrait (.pdf)",
    "PDF file landscape (.pdf)",
)

WELCOME_MD = """# Mark Converter

Markdown Viewer & Converter.

Open a Markdown file with **Open...** (`Ctrl + O`) to render it as HTML5 here.
Use **Convert...** (`Ctrl + E`) to export the current document to HTML5,
plain text or PDF.
"""
