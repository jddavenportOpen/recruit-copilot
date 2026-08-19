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
_OBJ = re.compile(rb"(?P<num>\d+)\s+\d+\s+obj\b(?P<body>.*?)\bendobj", re.S)
# Text-showing and font-selecting operators. Hex strings matter: Google Docs, Word
# and most browser "print to PDF" paths emit <hex> with CID fonts, and an extractor
# that only understands (literal) strings silently returns nothing on those files.
_NUM = r"-?[\d.]+"
_SHOW = re.compile(
    r"/(?P<font>[^\s/<>\[\]()]+)\s+(?P<size>[\d.]+)\s+Tf"
    r"|(?P<lit>\((?:[^()\\]|\\.)*\))\s*Tj"
    r"|(?P<hex><[0-9A-Fa-f\s]*>)\s*Tj"
    r"|(?P<arr>\[(?:[^\[\]\\]|\\.)*\])\s*TJ"
    rf"|(?P<td>{_NUM})\s+(?P<tdy>{_NUM})\s+(?:Td|TD)"
    rf"|{_NUM}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s+(?P<tmx>{_NUM})\s+(?P<tmy>{_NUM})\s+Tm"
    r"|(?P<star>\bT\*)|(?P<et>\bET\b)")
_STR_IN_ARR = re.compile(r"\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>|-?\d+(?:\.\d+)?")
# A kern this wide is a word gap, not letter spacing. CID-font producers routinely
# express spaces this way instead of emitting a space glyph.
_KERN_SPACE = 180.0


def _run_width(text: str, size: float) -> float:
    """Width of a text run in points, using the Helvetica metrics this package
    already ships. Falls back to a flat estimate if that module is unavailable."""
    try:
        from pdfwrite import text_width
        return text_width(text, size)
    except Exception:
        return 0.5 * size * len(text)


def _objects(data: bytes) -> dict:
    return {int(m.group("num")): m.group("body") for m in _OBJ.finditer(data)}


def _deref(objs: dict, blob: bytes):
    """Follow a `N 0 R` reference to its object body; pass anything else through."""
    m = re.match(rb"\s*(\d+)\s+\d+\s+R\b", blob or b"")
    return objs.get(int(m.group(1)), b"") if m else blob


def _stream_of(body: bytes) -> bytes:
    m = _STREAM.search(body)
    if not m:
        return b""
    names = re.findall(rb"/(\w+)Decode|/(A85|Fl|AHx)\b", m.group("dict"))
    return decode_stream(m.group("body"),
                         [(a or b).decode() + ("Decode" if a else "") for a, b in names])


def _parse_cmap(cmap: bytes) -> dict:
    """Parse a /ToUnicode CMap into {code: text}.

    This is what makes a CID-font PDF readable at all: the bytes in the content
    stream are glyph ids, and this table is the only thing that maps them back to
    characters."""
    out, s = {}, cmap.decode("latin-1", "replace")

    def uni(h: str) -> str:
        h = re.sub(r"\s", "", h)
        if not h:
            return ""
        try:
            return bytes.fromhex(h if len(h) % 2 == 0 else h + "0").decode("utf-16-be", "replace")
        except Exception:
            return ""

    for blk in re.findall(r"beginbfchar(.*?)endbfchar", s, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]*)>", blk):
            out[int(re.sub(r"\s", "", src), 16)] = uni(dst)
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", s, re.S):
        # <lo> <hi> [<d1> <d2> ...]
        for lo, hi, arr in re.findall(r"<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]+)>\s*\[(.*?)\]", blk, re.S):
            start = int(re.sub(r"\s", "", lo), 16)
            for i, d in enumerate(re.findall(r"<([0-9A-Fa-f\s]*)>", arr)):
                out[start + i] = uni(d)
        # <lo> <hi> <dst-start>
        for lo, hi, dst in re.findall(r"<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]*)>", blk):
            a, b = int(re.sub(r"\s", "", lo), 16), int(re.sub(r"\s", "", hi), 16)
            d = re.sub(r"\s", "", dst)
            if not d or b - a > 65535:
                continue
            base = int(d, 16)
            width = len(d) // 4 if len(d) > 4 else 1
            for i in range(b - a + 1):
                if width > 1:                       # multi-char destination: only the first shifts
                    out.setdefault(a + i, uni(d))
                else:
                    out[a + i] = chr(base + i) if 0 <= base + i <= 0x10FFFF else ""
    return out


def _fonts(data: bytes) -> dict:
    """{resource-name: (cmap, bytes_per_code)} merged across pages.

    Resource names repeat across pages, so this prefers the first mapping it finds
    for a name; for the single- and two-page documents this tool reads, that is
    right far more often than guessing."""
    objs = _objects(data)
    fonts: dict = {}
    for body in objs.values():
        fdict = re.search(rb"/Font\s*<<(?P<f>.*?)>>", body, re.S)
        if not fdict:
            continue
        for name, num in re.findall(rb"/([^\s/<>\[\]()]+)\s+(\d+)\s+\d+\s+R", fdict.group("f")):
            key = name.decode("latin-1")
            if key in fonts:
                continue
            fobj = objs.get(int(num), b"")
            two = b"/Type0" in fobj or b"Identity-H" in fobj or b"/Encoding /Identity" in fobj
            tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", fobj)
            cmap = _parse_cmap(_stream_of(objs.get(int(tu.group(1)), b""))) if tu else {}
            if cmap or two:
                fonts[key] = (cmap, 2 if two else 1)
    return fonts


def _decode_str(tok: str, font) -> str:
    """Turn one PDF string token into text, through the font's CMap when there is one."""
    if tok.startswith("<"):
        h = re.sub(r"\s", "", tok[1:-1])
        if len(h) % 2:
            h += "0"
        raw = bytes.fromhex(h) if h else b""
    else:
        raw = unescape(tok[1:-1]).encode("latin-1", "replace")
    if not font:
        return raw.decode("latin-1", "replace")
    cmap, width = font
    if width == 2:
        codes = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw) - 1, 2)]
    else:
        codes = list(raw)
    if not cmap:
        # Identity CID with no ToUnicode: the codes are glyph ids we cannot name.
        return "".join(chr(c) for c in codes if 32 <= c < 0x3000)
    return "".join(cmap.get(c, "") for c in codes)


def text_from_bytes(data: bytes) -> str:
    """Replay every content stream's text-showing operators in order."""
    fonts = _fonts(data)
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
        cur = None
        # Track the ABSOLUTE text position. Tm sets the line matrix; Td translates it.
        # Google Docs sets Tm once per BT block and then does the real move with Td, so
        # looking at either operator alone reads every word as its own line.
        cur_x = cur_y = 0.0
        line_y = None
        size = 10.0      # current font size, from Tf
        pen_x = None     # where the previous run is estimated to have ended

        def flush():
            nonlocal pen_x
            if line:
                chunks.append("".join(line))
                line.clear()
            pen_x = None

        def at_text():
            """Called before drawing: decide whether we moved to a new line, and
            whether the horizontal gap since the last run is a real word space.

            Runs that continue a word are laid down contiguously (the gap is ~0),
            while two fields on one line -- a company and a right-aligned location --
            are separated by a visible gap. Without this, they are glued together
            and the words are lost."""
            nonlocal line_y, pen_x
            if line_y is None:
                line_y = cur_y
            elif abs(cur_y - line_y) > 0.8:
                flush()
                line_y = cur_y
            if pen_x is not None and cur_x - pen_x > 0.3 * size and line and not line[-1].endswith(" "):
                line.append(" ")

        def advance(text):
            """Estimate where this run ended, so the next run's offset can be read as
            'touching' or 'a gap away'. Real Helvetica metrics when we have them: a
            flat per-character guess under-measures wide letters and invents spaces
            in the middle of words."""
            nonlocal pen_x
            pen_x = cur_x + _run_width(text, size)

        for tm in _SHOW.finditer(s):
            g = tm.group
            if g("font") is not None:
                cur = fonts.get(g("font"))
                try:
                    size = abs(float(g("size"))) or size
                except (TypeError, ValueError):
                    pass
            elif g("lit") is not None:
                at_text(); t = _decode_str(g("lit"), cur); line.append(t); advance(t)
            elif g("hex") is not None:
                at_text(); t = _decode_str(g("hex"), cur); line.append(t); advance(t)
            elif g("arr") is not None:
                at_text(); _n = len(line)
                for st in _STR_IN_ARR.finditer(g("arr")):
                    tok = st.group(0)
                    if tok[0] in "(<":
                        line.append(_decode_str(tok, cur))
                    else:
                        # a big negative kern is a space the producer never emitted
                        try:
                            if -float(tok) >= _KERN_SPACE and line and not line[-1].endswith(" "):
                                line.append(" ")
                        except ValueError:
                            pass
                advance("".join(line[_n:]))
            elif g("star") is not None:
                flush(); line_y = None
            elif g("et") is not None:
                # Deliberately NOT a line break: producers wrap every run in its own
                # BT/ET. Vertical position decides lines instead.
                pass
            elif g("tdy") is not None:
                cur_x += float(g("td")); cur_y += float(g("tdy"))
            elif g("tmy") is not None:
                cur_x, cur_y = float(g("tmx")), float(g("tmy"))
        flush()
    return "\n".join(c for c in chunks if c.strip())


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
