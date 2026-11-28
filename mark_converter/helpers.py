"""Theme persistence, temporary HTML files and Markdown conversion helpers."""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
from pathlib import Path

from markdown2html5_base import MarkdownToHTML

from mark_converter.constants import (
    CACHE_DIR,
    CONFIG_DIR,
    DEFAULT_THEME,
    TEMP_HTML,
    THEME_FILE,
    THEMES,
)

_BLOCKQUOTE_RE = re.compile(r"^[ \t]*>+[ \t]?")
_DEF_RE = re.compile(r"^\s*:\s+\S")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S")
_FOOTNOTE_RE = re.compile(r"^\[\^?[^\]]+\]:\s")


def _read_config() -> dict:
    """Read theme.json as a dict, falling back to an empty config."""
    with contextlib.suppress(OSError, ValueError, TypeError):
        data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    return {}


def _write_config(**updates) -> None:
    """Merge *updates* into theme.json, ignoring write failures."""
    with contextlib.suppress(OSError, TypeError, ValueError):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = _read_config()
        data.update(updates)
        THEME_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_theme() -> str:
    """Load the saved appearance mode from the theme config."""
    name = str(_read_config().get("mode", DEFAULT_THEME)).lower()
    return name if name in THEMES else DEFAULT_THEME


def save_theme(name: str) -> None:
    """Save the current appearance mode."""
    _write_config(mode=name)


def ensure_cache_dir() -> Path:
    """Create and return the Mark Converter cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_temp_html_path(current_file: Path | None) -> Path:
    """Return the temp HTML path used to render the current document.

    - No file opened: ``~/.cache/mark_converter/Temp.html``
    - File opened: ``<dir>/~<stem>.html`` (kept beside the source so that
      relative image links in the Markdown still resolve in WebKit)
    """
    if current_file is None:
        return ensure_cache_dir() / TEMP_HTML
    return current_file.parent / f"~{current_file.stem}.html"


def save_temp_html(html: str, current_file: Path | None) -> Path:
    """Save HTML content to the temp file and return its path."""
    path = get_temp_html_path(current_file)
    path.write_text(html, encoding="utf-8")
    return path


_converter: MarkdownToHTML | None = None


def get_converter() -> MarkdownToHTML:
    """Return the singleton MarkdownToHTML converter (lazy initialisation)."""
    global _converter
    if _converter is None:
        _converter = MarkdownToHTML()
    return _converter


def md_to_html(text: str, *, page_layout: str = "portrait") -> str:
    """Convert Markdown *text* to styled HTML5 using markdown2html5-base.

    ``page_layout`` is ``"portrait"`` (default) or ``"landscape"`` and selects
    the matching print CSS; every document embeds its styles.
    """
    return get_converter().convert(text, page_layout=page_layout)


def render_temp_html(
    text: str, current_file: Path | None, *, page_layout: str = "portrait"
) -> Path:
    """Convert Markdown to HTML5 and write it to the viewer's temp file."""
    return save_temp_html(md_to_html(text, page_layout=page_layout), current_file)


def _pdf_html_path(output: Path, source_file: Path | None) -> Path:
    """Return a free temporary HTML path for Chromium PDF printing."""
    if source_file is None:
        directory, stem = output.parent, "document"
    else:
        directory, stem = source_file.parent.resolve(), source_file.stem
    path = directory / f"{stem}.html"
    if not path.exists():
        return path
    alternate = directory / f"~~{stem}.html"
    if alternate.exists():
        raise FileExistsError(f"Temporary HTML file already exists: {alternate}")
    return alternate


def md_to_pdf(
    text: str,
    path: str,
    *,
    source_file: Path | None = None,
    page_layout: str = "portrait",
) -> None:
    """Save Markdown *text* as PDF via a temporary HTML5 file printed by Chromium."""
    output = Path(path).resolve()
    html_path = _pdf_html_path(output, source_file)
    try:
        html_path.write_text(
            md_to_html(text, page_layout=page_layout), encoding="utf-8"
        )
        subprocess.run(
            [
                "chromium",
                "--headless",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output}",
                str(html_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Chromium is required for PDF export") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(
            message or f"Chromium failed with code {exc.returncode}"
        ) from exc
    finally:
        html_path.unlink(missing_ok=True)


def _separate_lists(text: str) -> str:
    """Insert a blank line before ordered, unordered, todo and definition lists."""
    out: list[str] = []
    last: int | None = None
    in_list = False
    for line in text.split("\n"):
        if not line.strip():
            in_list = False
            out.append(line)
            continue
        if _LIST_RE.match(line):
            if not in_list and last is not None and out[last].strip():
                out.append("")
            in_list = True
            out.append(line)
            last = len(out) - 1
            continue
        if _DEF_RE.match(line):
            if (
                last is not None
                and out[last].strip()
                and not _LIST_RE.match(out[last])
                and not _DEF_RE.match(out[last])
                and not out[last].strip().startswith("```")
                and (last == 0 or out[last - 1].strip())
            ):
                out.insert(last, "")
                last += 1
            in_list = True
            out.append(line)
            last = len(out) - 1
            continue
        in_list = False
        out.append(line)
        last = len(out) - 1
    return "\n".join(out)


def _strip_blockquotes(text: str) -> str:
    """Remove ``>`` blockquote markers, keeping a blank line before each block."""
    out: list[str] = []
    in_quote = False
    for line in text.split("\n"):
        m = _BLOCKQUOTE_RE.match(line)
        if m is not None:
            if not in_quote and out and out[-1].strip():
                out.append("")
            in_quote = True
            out.append(line[m.end() :])
        else:
            in_quote = False
            out.append(line)
    return "\n".join(out)


def _compact_footnotes(text: str) -> str:
    """Drop blank lines that sit between consecutive footnote definitions."""
    lines = text.split("\n")
    out: list[str] = []
    prev = ""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            j = i
            while j < n and not lines[j].strip():
                j += 1
            between = (
                _FOOTNOTE_RE.match(prev) and j < n and _FOOTNOTE_RE.match(lines[j])
            )
            if between:
                i = j
                continue
        out.append(line)
        if line.strip():
            prev = line
        i += 1
    return "\n".join(out)


def _separate_code_blocks(text: str) -> str:
    """Insert a blank line after each fenced code block that has content next."""
    out: list[str] = []
    in_fence = False
    just_closed = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            out.append(line)
            in_fence = not in_fence
            just_closed = not in_fence
            continue
        if just_closed and line.strip():
            out.append("")
        just_closed = False
        out.append(line)
    return "\n".join(out)


def md_to_plain(text: str) -> str:
    """Strip Markdown syntax while preserving list, quote and table structure."""
    text = _separate_code_blocks(text)
    text = re.sub(r"^```[^\n]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#+\s?", "", text, flags=re.MULTILINE)
    text = _separate_lists(text)
    text = _strip_blockquotes(text)
    text = re.sub(r"^:[ \t]+", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*(\|[ \t]*)+$", "", text, flags=re.MULTILINE)
    footer_rows: list[str] = []

    def _mask_footer(m: re.Match) -> str:
        """Hide a ``| === |`` footer separator so ``=`` stripping skips it."""
        footer_rows.append(m.group(0))
        return f"\x00{len(footer_rows) - 1}\x00"

    text = re.sub(
        r"^[ \t]*\|[ \t]*([ \t]*=+[ \t]*\|)+$", _mask_footer, text, flags=re.MULTILINE
    )
    text = re.sub(
        r"^[ \t]*\|[ \t]*([ \t]*:?-{3,}:?[ \t]*\|)+$",
        lambda m: re.sub(r":?-{3,}:?", "---", m.group(0)),
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\[.*?\]:\s*#\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\{#[^}]*\}", "", text)
    text = re.sub(r"\{:[^}]*\}", "", text)
    text = re.sub(r"\{([^|}]+)\|([^}]*)\}", r"\1(\2)", text)
    text = re.sub(r"[*_~^`=]{1,2}", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _compact_footnotes(text)
    for i, row in enumerate(footer_rows):
        text = text.replace(f"\x00{i}\x00", row)
    return text.strip() + "\n"
