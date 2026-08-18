#!/usr/bin/env python3
"""A minimal, dependency-free PDF writer for single-column ATS resumes.

Why write our own instead of using reportlab: the whole product thesis is that a
resume has to survive being read by a machine. The maximally parseable artifact is
a single-column PDF using only the base-14 fonts (no embedded font programs, no
CID mapping, no images, no columns) with an UNCOMPRESSED content stream. That is
exactly what this emits, and it needs nothing but the standard library, so the
plugin stays install-free.

It also returns the layout it produced (every line's text and bounding box), so
format_qa.py can check the RENDERED page instead of guessing from the source text.

Coordinates are PDF points (72/inch), origin bottom-left, US Letter 612x792.
"""

from __future__ import annotations

# Base-14 Helvetica advance widths, 1/1000 em, ASCII 32..126.
_HELV = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
_HELV_B = [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584,
]

FONTS = {"regular": ("F1", "Helvetica", _HELV),
         "bold": ("F2", "Helvetica-Bold", _HELV_B),
         "italic": ("F3", "Helvetica-Oblique", _HELV)}

# Characters a tailoring model reaches for that are not in WinAnsi ASCII. Mapping
# them at render time is what keeps the extracted text byte-identical to the
# source text, which is what makes the round-trip check meaningful.
TRANSLIT = {
    "—": ", ", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
    "•": "-", "‑": "-", "ʼ": "'", "−": "-",
}


SUBSTITUTIONS: dict[str, int] = {}


def sanitize(text: str) -> str:
    """Fold typographic characters to ASCII. Anything still non-ASCII is dropped,
    because a base-14 font cannot render it and it would extract as garbage.

    Every substitution is counted in SUBSTITUTIONS so the caller can tell the user
    what changed. Fixing a document silently is how people end up surprised by
    their own resume."""
    for bad, good in TRANSLIT.items():
        if bad in text:
            SUBSTITUTIONS[bad] = SUBSTITUTIONS.get(bad, 0) + text.count(bad)
            text = text.replace(bad, good)
    kept = []
    for c in text:
        if 32 <= ord(c) <= 126 or c in "\n\t":
            kept.append(c)
        else:
            SUBSTITUTIONS["<dropped>"] = SUBSTITUTIONS.get("<dropped>", 0) + 1
    return "".join(kept)


def text_width(text: str, size: float, style: str = "regular") -> float:
    widths = FONTS[style][2]
    total = 0
    for ch in text:
        o = ord(ch)
        total += widths[o - 32] if 32 <= o <= 126 else widths[0]
    return total * size / 1000.0


def wrap(text: str, size: float, style: str, max_width: float) -> list[str]:
    """Greedy word wrap measured in real glyph widths, not character counts."""
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if text_width(trial, size, style) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


class Page:
    def __init__(self, width: float, height: float):
        self.width, self.height = width, height
        self.ops: list[str] = []
        self.lines: list[dict] = []   # layout record for format_qa

    def draw(self, text: str, x: float, y: float, size: float, style: str, kind: str = "body"):
        text = sanitize(text)
        if not text.strip():
            return
        fid = FONTS[style][0]
        self.ops.append(f"BT /{fid} {size:g} Tf 1 0 0 1 {x:g} {y:g} Tm ({_esc(text)}) Tj ET")
        w = text_width(text, size, style)
        self.lines.append({
            "text": text, "kind": kind, "size": size, "style": style,
            # bbox is x0, y0, x1, y1 with y measured from the TOP of the page, so
            # downstream checks read in the same direction a human reads.
            "bbox": [x, self.height - y - size, x + w, self.height - y],
        })

    def rule(self, x0: float, x1: float, y: float, thickness: float = 0.6):
        self.ops.append(f"{thickness:g} w {x0:g} {y:g} m {x1:g} {y:g} l S")


class Document:
    def __init__(self, width: float = 612.0, height: float = 792.0):
        self.width, self.height = width, height
        self.pages: list[Page] = []

    def new_page(self) -> Page:
        p = Page(self.width, self.height)
        self.pages.append(p)
        return p

    def layout(self) -> list[dict]:
        return [{"page": i + 1, "lines": p.lines} for i, p in enumerate(self.pages)]

    def to_bytes(self) -> bytes:
        """Serialize. Content streams are left uncompressed on purpose: any parser,
        including the one in parse_check.py, can read them without inflating."""
        objs: list[bytes] = []

        def add(body: bytes) -> int:
            objs.append(body)
            return len(objs)          # 1-based object number

        font_ids = {}
        for style, (fid, base, _w) in FONTS.items():
            font_ids[fid] = add(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /" + base.encode()
                + b" /Encoding /WinAnsiEncoding >>")

        pages_obj = len(objs) + 2 * len(self.pages) + 1
        kids, page_objs = [], []
        for page in self.pages:
            stream = "\n".join(page.ops).encode("latin-1", "replace")
            cid = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
                      + stream + b"\nendstream")
            res = b" ".join(b"/" + f.encode() + b" " + str(n).encode() + b" 0 R"
                            for f, n in font_ids.items())
            pid = add(b"<< /Type /Page /Parent " + str(pages_obj).encode()
                      + b" 0 R /MediaBox [0 0 " + f"{self.width:g} {self.height:g}".encode()
                      + b"] /Resources << /Font << " + res + b" >> >> /Contents "
                      + str(cid).encode() + b" 0 R >>")
            page_objs.append(pid)
            kids.append(str(pid).encode() + b" 0 R")

        add(b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count "
            + str(len(self.pages)).encode() + b" >>")
        root = add(b"<< /Type /Catalog /Pages " + str(pages_obj).encode() + b" 0 R >>")

        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
        for off in offsets[1:]:
            out += f"{off:010d} 00000 n \n".encode()
        out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root "
                + str(root).encode() + b" 0 R >>\nstartxref\n"
                + str(xref).encode() + b"\n%%EOF\n")
        return bytes(out)
