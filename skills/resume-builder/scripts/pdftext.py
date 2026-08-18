#!/usr/bin/env python3
"""Extract text from a PDF using only the standard library.

This exists because the tool has to read two kinds of PDF and cannot assume an
install for either one:

  1. The resumes you already have, which were produced by Word, Pages, LaTeX,
     reportlab, or a browser print, and which arrive with real filter chains.
     ASCII85 then Flate is what reportlab emits, and a decoder that only knows
     Flate silently returns nothing on those, which looks exactly like a scanned
     image and sends the user down the wrong path.
  2. The PDF this tool just wrote, for the round-trip check.

PyMuPDF is used when it is present, because it is a real text engine and handles
CID fonts and unusual encodings this cannot. This is the fallback, and it is
honest about being one.
"""

from __future__ import annotations

import base64
import re
import zlib

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
            "(": "(", ")": ")", "\\": "\\"}


def unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt]); i += 2; continue
            if nxt in "\r\n":                      # line continuation
                i += 2
                if nxt == "\r" and i < len(s) and s[i] == "\n":
                    i += 1
                continue
            m = re.match(r"[0-7]{1,3}", s[i + 1:i + 4])
            if m:
                out.append(chr(int(m.group(0), 8))); i += 1 + len(m.group(0)); continue
            out.append(nxt); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def _a85(data: bytes) -> bytes:
    body = re.sub(rb"\s", b"", data)
    if body.startswith(b"<~"):
        body = body[2:]
    end = body.find(b"~>")
    if end != -1:
        body = body[:end]
    return base64.a85decode(body)


def _flate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except zlib.error:
        # A truncated or slightly malformed stream still yields its valid prefix,
        # which is better than nothing when the goal is reading text.
        d = zlib.decompressobj()
        try:
            return d.decompress(data)
        except zlib.error:
            return zlib.decompressobj(-15).decompress(data)


def _ahx(data: bytes) -> bytes:
    body = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
    if len(body) % 2:
        body += b"0"
    return bytes.fromhex(body.decode("ascii"))


DECODERS = {"ASCII85Decode": _a85, "A85": _a85,
            "FlateDecode": _flate, "Fl": _flate,
            "ASCIIHexDecode": _ahx, "AHx": _ahx}


def decode_stream(raw: bytes, filters: list[str]) -> bytes:
    """Apply a declared filter chain, then fall back to sniffing if it fails.

    Sniffing matters: plenty of real PDFs carry a filter name this does not know
    (LZW, JBIG2) or an indirect /Filter reference that cannot be resolved without
    a full object graph. Trying the two common chains recovers most of those."""
    data = raw
    try:
        for f in filters:
            fn = DECODERS.get(f)
            if fn is None:
                raise ValueError(f"unsupported filter {f}")
            data = fn(data)
        return data
    except Exception:
        pass
    for chain in (( _a85, _flate), (_flate,), (_a85,), (_ahx, _flate), ()):
        try:
            out = raw
            for fn in chain:
                out = fn(out)
            if b"Tj" in out or b"TJ" in out:
                return out
        except Exception:
            continue
    return b""


_STREAM = re.compile(rb"<<(?P<dict>.*?)>>\s*stream\r?\n?(?P<body>.*?)\r?\n?endstream", re.S)
_SHOW = re.compile(
    r"\((?:[^()\\]|\\.)*\)\s*Tj|\[(?:[^\[\]\\]|\\.)*\]\s*TJ|\bT\*|\bTd\b|\bTD\b|\bTm\b|\bET\b")


def text_from_bytes(data: bytes) -> str:
    """Replay every content stream's text-showing operators in order."""
    chunks: list[str] = []
    for m in _STREAM.finditer(data):
        names = re.findall(rb"/(\w+)Decode|/(A85|Fl|AHx)\b", m.group("dict"))
        filters = [(a or b).decode() + ("Decode" if a else "")
                   for a, b in names]
        body = decode_stream(m.group("body"), filters)
        if b"Tj" not in body and b"TJ" not in body:
            continue
        s = body.decode("latin-1", "replace")
        line: list[str] = []
        for tm in _SHOW.finditer(s):
            tok = tm.group(0)
            if tok.endswith("Tj"):
                line.append(unescape(tok[1:tok.rindex(")")]))
            elif tok.endswith("TJ"):
                for st in re.finditer(r"\((?:[^()\\]|\\.)*\)", tok):
                    line.append(unescape(st.group(0)[1:-1]))
            elif line:
                chunks.append("".join(line)); line = []
        if line:
            chunks.append("".join(line))
    return "\n".join(chunks)


def extract(path: str) -> tuple[str, str]:
    """Returns (text, engine). Prefers PyMuPDF when the user has it."""
    try:
        import fitz
        doc = fitz.open(path)
        text = "".join(p.get_text() for p in doc)
        doc.close()
        if text.strip():
            return text, "pymupdf"
    except Exception:
        pass
    return text_from_bytes(open(path, "rb").read()), "stdlib"
