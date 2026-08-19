#!/usr/bin/env python3
"""Layout QA on the RENDERED page, not on the source text.

A resume can read perfectly as text and still land badly: the contact line wraps
to two rows, a bullet runs five lines, a section header is orphaned at the foot of
a page, a long URL overruns the margin. A text-based score cannot see any of that,
because none of it exists until the thing is typeset. This measures the page.

It reads the .layout.json that render_resume.py writes alongside the PDF, so every
check is against real glyph positions rather than a character-count guess.

Exit 0 pass, 1 fail. As a library: analyze(layout, target_pages) -> dict.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

OVERFLOW_SLACK = 1.5
OVERFLOW_HARD = 6.0        # past this the text is off the page, not merely tight
COLLISION_SLACK = 0.5      # two runs on one baseline may touch, never overlap
MAX_BULLET_LINES = 2
MAX_BULLET_LINES_WITH_URL = 3
MIN_BULLET_WORDS = 4
SECTION_HEADERS = {"SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS",
                   "ADDITIONAL INFORMATION", "PROJECTS", "CERTIFICATIONS"}
URL_MARK = re.compile(r"https?://|\bwww\.|\.com/|\.io/|\.dev/|\.org/|github\.com|linkedin\.com")
BANNED = {"—": "em dash", "–": "en dash", "’": "curly apostrophe", "•": "bullet glyph"}


def analyze(layout: dict, target_pages: int | None = None) -> dict:
    issues = []
    stats = {"pages": layout.get("pages", 0), "bullets": 0, "max_bullet_lines": 0,
             "widest_overrun": 0.0, "collisions": 0}
    right_edge = layout.get("text_right_edge", 558.0)

    def add(level, code, detail, **extra):
        issues.append({"level": level, "code": code, "detail": detail, **extra})

    if target_pages and stats["pages"] > target_pages:
        add("error", "page_overflow",
            f"{stats['pages']} pages, target is {target_pages}; cut bullets or a whole role")
    if stats["pages"] == 0:
        add("error", "empty_document", "nothing rendered")
        return _result(issues, stats)

    pages = layout.get("content", [])

    for page in pages:
        pno = page["page"]
        lines = page.get("lines", [])

        # contact line must be exactly one row
        if pno == 1:
            contact = [l for l in lines if l["kind"] == "contact"]
            if len(contact) > 1:
                add("error", "contact_wrap",
                    f"contact spans {len(contact)} lines; drop an item so it fits one row")

        # nothing may cross the right margin
        for l in lines:
            over = l["bbox"][2] - right_edge
            if over > OVERFLOW_SLACK:
                stats["widest_overrun"] = max(stats["widest_overrun"], over)
                add("error" if over > OVERFLOW_HARD else "warn", "margin_overflow",
                    f"p{pno}: {over:.0f}pt past the right margin: {l['text'][:44]!r}")

        # two runs sharing a baseline must not print on top of each other. This is
        # the defect a text-based check can never see and the round trip cannot
        # either: overlapping glyphs still extract as clean, complete text, so the
        # file reads fine to a parser and is unreadable to a person. Only the
        # measured page shows it.
        rows = {}
        for l in lines:
            rows.setdefault(round(l["bbox"][1], 1), []).append(l)
        for base in sorted(rows):
            run = sorted(rows[base], key=lambda l: l["bbox"][0])
            for a, b in zip(run, run[1:]):
                over = a["bbox"][2] - b["bbox"][0]
                if over > COLLISION_SLACK:
                    stats["collisions"] += 1
                    add("error", "text_collision",
                        f"p{pno}: {over:.0f}pt of overlapping text: {a['text'][:26]!r} "
                        f"prints over {b['text'][:26]!r}")

        # a bullet broken across a page break leaves widow lines the grouping below
        # would otherwise drop on the floor, so the bullet is never measured at all
        if lines and lines[0]["kind"] == "bullet_cont":
            add("warn", "split_bullet",
                f"p{pno} opens mid-bullet: {lines[0]['text'][:44]!r}; move it whole or cut it")

        # bullets: measured line spans, not character estimates
        cur, groups = None, []
        for l in lines:
            if l["kind"] == "bullet":
                if cur:
                    groups.append(cur)
                cur = [l]
            elif l["kind"] == "bullet_cont" and cur:
                cur.append(l)
            elif l["kind"] not in ("bullet_glyph",):
                if cur:
                    groups.append(cur); cur = None
        if cur:
            groups.append(cur)

        for g in groups:
            stats["bullets"] += 1
            n = len(g)
            stats["max_bullet_lines"] = max(stats["max_bullet_lines"], n)
            text = " ".join(x["text"] for x in g)
            cap = MAX_BULLET_LINES_WITH_URL if URL_MARK.search(text) else MAX_BULLET_LINES
            if n > cap:
                add("error" if n >= cap + 2 else "warn", "long_bullet",
                    f"p{pno}: bullet runs {n} lines (max {cap}): {g[0]['text'][:44]!r}",
                    text_prefix=g[0]["text"][:36])
            if len(text.split()) < MIN_BULLET_WORDS:
                add("warn", "thin_bullet",
                    f"p{pno}: bullet is only {len(text.split())} words: {text[:44]!r}")

        # a section header alone at the foot of a non-final page
        if pno < stats["pages"] and lines:
            tail = [l for l in lines if l["kind"] != "bullet_glyph"][-1:]
            if tail and tail[0]["text"].strip().upper() in SECTION_HEADERS:
                add("warn", "orphan_header",
                    f"p{pno}: '{tail[0]['text'].strip()}' is stranded at the page bottom")

    # the renderer folds these to ASCII on the way in, so finding one on the page
    # means that folding did not happen and the character will extract as mojibake
    for page in pages:
        for l in page.get("lines", []):
            for ch, label in BANNED.items():
                if ch in l["text"]:
                    add("error", "banned_glyph",
                        f"p{page['page']}: a {label} survived to the page in "
                        f"{l['text'][:40]!r}; it will not extract cleanly")

    # what the renderer had to change to make the document parseable. It fixes these
    # rather than failing on them, but you should know it happened.
    for note in layout.get("notes", []):
        add("warn", "render_fixup", note)

    # a mostly-empty last page reads as a formatting accident
    if stats["pages"] > 1:
        last = pages[-1].get("lines", [])
        if 0 < len(last) <= 3:
            add("warn", "runt_page",
                f"page {stats['pages']} holds only {len(last)} lines; tighten to fit "
                f"{stats['pages'] - 1} pages")

    return _result(issues, stats)


def _result(issues, stats):
    errors = [i for i in issues if i["level"] == "error"]
    return {"passed": not errors, "errors": len(errors),
            "warnings": len(issues) - len(errors), "issues": issues, "stats": stats}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="the rendered PDF, or its .layout.json")
    ap.add_argument("--target-pages", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    path = a.target
    if path.endswith(".pdf"):
        path = os.path.splitext(path)[0] + ".layout.json"
    if not os.path.exists(path):
        print(f"no layout record at {path}; render with render_resume.py first", file=sys.stderr)
        sys.exit(2)

    r = analyze(json.load(open(path)), a.target_pages)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        s = r["stats"]
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['errors']} error(s), "
              f"{r['warnings']} warning(s) | {s['pages']}p, {s['bullets']} bullets, "
              f"longest bullet {s['max_bullet_lines']} lines, "
              f"{s['collisions']} collision(s)")
        for i in r["issues"]:
            print(f"  {i['level'].upper():5} {i['code']}: {i['detail']}")
    sys.exit(0 if r["passed"] else 1)


if __name__ == "__main__":
    main()
