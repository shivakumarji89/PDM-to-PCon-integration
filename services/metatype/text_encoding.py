"""Encoding-preserving append for ``go_texts.csv`` (decision D5). Pure: returns bytes, never writes.

Verified (46 non-empty real go_texts.csv): 40 are single-byte Windows-1252, 2 are UTF-8, 4 are pure ASCII; line
endings are CRLF in all 46. The rule implemented is therefore: *preserve the file's own convention*.

* BOM: kept exactly (a UTF-8 BOM implies UTF-8).
* valid UTF-8 with non-ASCII -> UTF-8; invalid UTF-8 that decodes strictly as Windows-1252 -> cp1252;
  invalid in both, or containing both valid UTF-8 multibyte sequences and invalid bytes -> ``AMBIGUOUS`` (refused).
* empty or pure-ASCII file: new non-ASCII text needs an encoding chosen by the owner (the recommendation is
  Windows-1252 but is not confirmed); with no ``fallback`` the result is refused. Pure-ASCII new text needs none.
* Line ending: that of the existing file; mixed endings are refused; an empty file has no convention, so the caller
  must pass one. Existing bytes are never altered; text is appended after making sure the file ends with a break.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_BOM = b"\xef\xbb\xbf"
_UTF8_MULTI = re.compile(rb"[\xc2-\xdf][\x80-\xbf]|[\xe0-\xef][\x80-\xbf]{2}|[\xf0-\xf4][\x80-\xbf]{3}")


class Encoding(str, Enum):
    EMPTY = "empty"
    ASCII = "ascii"
    UTF8 = "utf-8"
    UTF8_BOM = "utf-8-sig"
    CP1252 = "cp1252"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class AppendResult:
    data: bytes | None
    encoding: Encoding
    problems: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.data is not None and not self.problems


def detect_encoding(raw: bytes) -> Encoding:
    if not raw:
        return Encoding.EMPTY
    if raw.startswith(_BOM):
        try:
            raw[3:].decode("utf-8")
            return Encoding.UTF8_BOM
        except UnicodeDecodeError:
            return Encoding.AMBIGUOUS
    try:
        text = raw.decode("utf-8")
        return Encoding.ASCII if text.isascii() else Encoding.UTF8
    except UnicodeDecodeError:
        pass
    if _UTF8_MULTI.search(raw):
        return Encoding.AMBIGUOUS
    try:
        raw.decode("cp1252")
        return Encoding.CP1252
    except UnicodeDecodeError:
        return Encoding.AMBIGUOUS


def detect_line_ending(raw: bytes) -> str | None:
    """The single line ending used, or ``None`` when there is none or several."""
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    cr = raw.count(b"\r") - crlf
    kinds = [(n, e) for n, e in ((crlf, "\r\n"), (lf, "\n"), (cr, "\r")) if n]
    return kinds[0][1] if len(kinds) == 1 else None


def append_text_lines(raw: bytes, lines: list[str], fallback: Encoding | None = None,
                      default_eol: str | None = None) -> AppendResult:
    """Append ``lines`` (without terminators) to ``raw`` in the file's own encoding and line ending."""
    encoding = detect_encoding(raw)
    if encoding is Encoding.AMBIGUOUS:
        return AppendResult(None, encoding, ("The file's encoding is ambiguous; it is not rewritten.",))
    for line in lines:
        if "\r" in line or "\n" in line:
            return AppendResult(None, encoding, (f"Line {line!r} contains a line break.",))
    has_break = b"\n" in raw or b"\r" in raw
    eol = detect_line_ending(raw) if has_break else default_eol
    if eol is None:
        return AppendResult(None, encoding, (
            "The file's line endings are mixed or it has none and no convention was supplied; not rewritten.",))
    text = "".join(line + eol for line in lines)
    target = encoding
    if encoding in (Encoding.EMPTY, Encoding.ASCII) and not text.isascii():
        if fallback in (Encoding.CP1252, Encoding.UTF8):
            target = fallback
        else:
            return AppendResult(None, encoding, (
                "New non-ASCII text needs an encoding for an empty or ASCII-only file; the owner has not "
                "decided (decision D5).",))
    codec = {Encoding.EMPTY: "ascii", Encoding.ASCII: "ascii", Encoding.UTF8: "utf-8", Encoding.UTF8_BOM: "utf-8",
             Encoding.CP1252: "cp1252"}[target]
    try:
        body = text.encode(codec)
    except UnicodeEncodeError as exc:
        return AppendResult(None, target, (f"The text cannot be encoded as {codec}: {exc}",))
    prefix = raw
    if raw and not raw.endswith((b"\n", b"\r")):
        prefix += eol.encode("ascii")
    return AppendResult(prefix + body, target)
