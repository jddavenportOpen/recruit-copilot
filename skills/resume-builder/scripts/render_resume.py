#!/usr/bin/env python3
"""Render a tailored resume JSON to a single-column, ATS-safe PDF.

Single column, base-14 fonts only, no images, no tables, no text boxes, standard
section headers, dates as MM/YYYY. Every one of those is a parser-compatibility
decision, not a taste decision.

Emits <out>.pdf and <out>.layout.json (what actually landed on the page, for
format_qa.py to measure).

Usage:
    python3 render_resume.py resume.json --out workspace/resumes/acme-pm.pdf [--pages 1]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdfwrite as P  # noqa: E402

MARGIN_X = 54.0
MARGIN_TOP = 52.0
MARGIN_BOT = 46.0
PAGE_W, PAGE_H = 612.0, 792.0
TEXT_W = PAGE_W - 2 * MARGIN_X

NAME_SIZE, CONTACT_SIZE = 15.0, 8.8
HEAD_SIZE, BODY_SIZE = 9.6, 9.2
BULLET_INDENT = 11.0
SECTION_ORDER = ("SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS", "ADDITIONAL INFORMATION")


class Cursor:
    def __init__(self, doc):
        self.doc = doc
        self.page = doc.new_page()
        self.y = PAGE_H - MARGIN_TOP

    def space(self, n):
        self.y -= n

    def need(self, n):
        """Break the page if n points will not fit above the bottom margin."""
        if self.y - n < MARGIN_BOT:
            self.page = self.doc.new_page()
            self.y = PAGE_H - MARGIN_TOP
            return True
        return False

    def line(self, text, size, style, kind="body", x=MARGIN_X, gap=1.9):
        self.need(size + gap)
        self.y -= size
        self.page.draw(text, x, self.y, size, style, kind)
        self.y -= gap

    def para(self, text, size, style, kind="body", x=MARGIN_X, width=None, gap=1.9):
        for ln in P.wrap(text, size, style, width or (PAGE_W - MARGIN_X - x)):
            self.line(ln, size, style, kind, x, gap)

    def bullet(self, text, size=BODY_SIZE):
        """Hanging indent. The glyph is a plain ASCII hyphen because every parser
        handles it; a fancy bullet is a common source of mojibake in extraction."""
        width = TEXT_W - BULLET_INDENT
        lines = P.wrap(P.sanitize(text), size, "regular", width)
        for i, ln in enumerate(lines):
            self.need(size + 1.9)
            self.y -= size
            if i == 0:
                self.page.draw("-", MARGIN_X, self.y, size, "regular", "bullet_glyph")
            self.page.draw(ln, MARGIN_X + BULLET_INDENT, self.y, size, "regular",
                           "bullet" if i == 0 else "bullet_cont")
            self.y -= 1.9

    def section(self, title):
        self.need(HEAD_SIZE + 14)
        self.space(7)
        self.y -= HEAD_SIZE
        self.page.draw(title.upper(), MARGIN_X, self.y, HEAD_SIZE, "bold", "header")
        self.page.rule(MARGIN_X, PAGE_W - MARGIN_X, self.y - 3.2)
        self.y -= 8.0


def render(resume: dict, out_path: str) -> dict:
    P.SUBSTITUTIONS.clear()
    notes: list[str] = []
    doc = P.Document(PAGE_W, PAGE_H)
    c = Cursor(doc)

    c.line(resume.get("name", ""), NAME_SIZE, "bold", "name")
    contact = resume.get("contact", "")
    if contact:
        # A wrapped contact line is a real defect (format_qa flags it), so drop
        # trailing items until it fits rather than silently wrapping.
        parts = [p.strip() for p in contact.split("|") if p.strip()]
        dropped = []
        while len(parts) > 1 and P.text_width(" | ".join(parts), CONTACT_SIZE, "regular") > TEXT_W:
            dropped.append(parts.pop())
        if dropped:
            notes.append("contact line did not fit on one row, so these were dropped: "
                         + ", ".join(reversed(dropped)))
        c.line(" | ".join(parts), CONTACT_SIZE, "regular", "contact")

    if resume.get("summary"):
        c.section("Summary")
        c.para(resume["summary"], BODY_SIZE, "regular", "summary", width=TEXT_W)

    if resume.get("jobs"):
        c.section("Experience")
        for job in resume["jobs"]:
            c.need(BODY_SIZE * 3)
            left = f"{job.get('company','')}"
            right = job.get("dates", "")
            c.y -= BODY_SIZE
            c.page.draw(left, MARGIN_X, c.y, BODY_SIZE, "bold", "employer")
            if right:
                w = P.text_width(right, BODY_SIZE, "regular")
                c.page.draw(right, PAGE_W - MARGIN_X - w, c.y, BODY_SIZE, "regular", "dates")
            c.y -= 1.9
            role = job.get("title", "")
            loc = job.get("location", "")
            if role or loc:
                c.y -= BODY_SIZE
                c.page.draw(role, MARGIN_X, c.y, BODY_SIZE, "italic", "role")
                if loc:
                    w = P.text_width(loc, BODY_SIZE, "italic")
                    c.page.draw(loc, PAGE_W - MARGIN_X - w, c.y, BODY_SIZE, "italic", "location")
                c.y -= 2.4
            for b in job.get("bullets", []):
                c.bullet(b if isinstance(b, str) else b.get("text", ""))
            c.space(3.4)

    if resume.get("education"):
        c.section("Education")
        for e in resume["education"]:
            c.need(BODY_SIZE * 2)
            c.y -= BODY_SIZE
            c.page.draw(e.get("school", ""), MARGIN_X, c.y, BODY_SIZE, "bold", "school")
            if e.get("dates"):
                w = P.text_width(e["dates"], BODY_SIZE, "regular")
                c.page.draw(e["dates"], PAGE_W - MARGIN_X - w, c.y, BODY_SIZE, "regular", "dates")
            c.y -= 1.9
            detail = ", ".join(x for x in (e.get("degree"), e.get("detail")) if x)
            if detail:
                c.para(detail, BODY_SIZE, "regular", "edu_detail", width=TEXT_W)
            c.space(2.2)

    skills = resume.get("skills") or {}
    if skills:
        c.section("Skills")
        for cat, items in skills.items():
            val = items if isinstance(items, str) else ", ".join(items)
            label = f"{cat}: "
            lw = P.text_width(label, BODY_SIZE, "bold")
            first = P.wrap(val, BODY_SIZE, "regular", TEXT_W - lw)
            c.need(BODY_SIZE + 1.9)
            c.y -= BODY_SIZE
            c.page.draw(label, MARGIN_X, c.y, BODY_SIZE, "bold", "skill_label")
            c.page.draw(first[0], MARGIN_X + lw, c.y, BODY_SIZE, "regular", "skill_value")
            c.y -= 1.9
            for ln in first[1:]:
                c.line(ln, BODY_SIZE, "regular", "skill_value", MARGIN_X + lw)

    if resume.get("additional"):
        c.section("Additional Information")
        c.para(resume["additional"], BODY_SIZE, "regular", "additional", width=TEXT_W)

    data = doc.to_bytes()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    for ch, n in sorted(P.SUBSTITUTIONS.items()):
        label = {"<dropped>": "unrenderable character(s) removed"}.get(
            ch, f"{ch!r} replaced ({P.TRANSLIT.get(ch, '')!r})")
        notes.append(f"{n} x {label}")
    layout = {"pages": len(doc.pages), "page_width": PAGE_W, "page_height": PAGE_H,
              "text_right_edge": PAGE_W - MARGIN_X, "notes": notes, "content": doc.layout()}
    with open(os.path.splitext(out_path)[0] + ".layout.json", "w") as f:
        json.dump(layout, f, indent=1)
    return layout


def laid_out_text(layout: dict) -> str:
    """Everything the typesetter actually placed on the page.

    This is the left-hand side of the round-trip. Comparing it to text extracted
    from the finished FILE tests serialization and encoding: escaping faults, a
    truncated content stream, a broken xref, glyphs that do not survive the font
    encoding. It is deliberately NOT compared against the input JSON, because the
    renderer makes reported, intentional edits (a contact line that will not fit),
    and folding those in here would report one problem as two."""
    return " ".join(l["text"] for p in layout.get("content", []) for l in p.get("lines", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("resume_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=None, help="target page count, for QA")
    a = ap.parse_args()
    resume = json.load(open(a.resume_json))
    layout = render(resume, a.out)
    print(f"rendered {a.out} ({layout['pages']} page(s))")
    for n in layout.get("notes", []):
        print(f"  changed: {n}")
    if a.pages and layout["pages"] > a.pages:
        print(f"  over target: {layout['pages']} pages vs {a.pages}", file=sys.stderr)


if __name__ == "__main__":
    main()
