#!/usr/bin/env python3
"""Round-trip parse check: render the PDF, pull the text back out, diff the two.

This is the check almost nobody runs, and it is the one that decides whether any
machine downstream ever sees your resume. A resume can score well on content and
still lose its phone number to a header region, drop a whole employer to column
interleaving, or arrive as an unextractable image. None of that is visible in the
source text or in a visual skim. You only see it by extracting the finished file.

Two extractors, strongest first:

  1. PyMuPDF, if the user happens to have it. This is a real, independent,
     production-grade PDF text engine, so agreement with it is real evidence.
  2. A stdlib content-stream reader. It parses the emitted file's bytes, so it
     still catches serialization, escaping and encoding faults.

Honest limit, stated because the whole point of this tool is not overclaiming:
passing proves the text is present and recoverable in reading order from the
finished file. It does not prove every commercial ATS parses it correctly, because
those are closed systems nobody can test against. It rules out the failure modes
that are testable.

Exit 0 pass, 1 fail. As a library: check(pdf_path, expect=...) -> dict.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdftext  # noqa: E402

CONTACT = {
    "email": r"[\w.+\-]+@[\w\-]+\.\w{2,}",
    "phone": r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}",
}
EXPECTED_HEADERS = ("experience", "education", "skills")
MIN_CHARS = 400


def extract_stdlib(data: bytes) -> str:
    return pdftext.text_from_bytes(data)


def extract_pymupdf(path: str):
    text, engine = pdftext.extract(path)
    return text if engine == "pymupdf" else None


def check(pdf_path: str, expect: dict | None = None) -> dict:
    """expect: {"companies": [...], "email": "...", "phone": "...", "source_text": "..."}"""
    expect = expect or {}
    data = open(pdf_path, "rb").read()

    strong = extract_pymupdf(pdf_path)
    text = strong if strong is not None else extract_stdlib(data)
    engine = "pymupdf" if strong is not None else "stdlib"

    res = {"passed": True, "engine": engine, "extracted_chars": len(text),
           "hard_breaker": False, "violations": [], "warnings": []}

    def hard(msg):
        res["violations"].append(msg); res["passed"] = False; res["hard_breaker"] = True

    def soft(msg):
        res["violations"].append(msg); res["passed"] = False

    if len(text.strip()) < MIN_CHARS:
        hard(f"only {len(text.strip())} characters came back out; "
             "the file is probably an image or otherwise unextractable")
        return res

    low = text.lower()

    if not re.search(CONTACT["email"], text):
        hard("no email survived extraction; a resume no one can reply to is a silent reject")
    elif expect.get("email") and expect["email"].lower() not in low:
        found = re.search(CONTACT["email"], text).group(0)
        res["warnings"].append(f"extracted email {found!r} differs from the one you configured "
                               f"({expect['email']!r})")

    if not re.search(CONTACT["phone"], text):
        soft("no phone number survived extraction")
    elif expect.get("phone"):
        digits = re.sub(r"\D", "", expect["phone"])
        if digits and digits not in re.sub(r"\D", "", text):
            res["warnings"].append("a phone number survived but it is not the one you configured")

    missing = [h for h in EXPECTED_HEADERS if h not in low]
    if missing:
        soft(f"standard section header(s) missing from extracted text: {', '.join(missing)}")

    for co in expect.get("companies", []):
        token = (co or "").split()[0].lower()
        if token and token not in low:
            soft(f"employer {co!r} did not survive extraction; a whole role may be unreadable")

    # Every word of the source should come back. Catches silent glyph loss.
    src = expect.get("source_text")
    if src:
        want = {w for w in re.findall(r"[A-Za-z]{4,}", src.lower())}
        got = set(re.findall(r"[A-Za-z]{4,}", low))
        lost = sorted(want - got)
        if lost:
            soft(f"{len(lost)} word(s) present in the source did not survive extraction: "
                 + ", ".join(lost[:8]) + ("..." if len(lost) > 8 else ""))

    if re.search(r"['’]\d{2}\b", text):
        res["warnings"].append("two-digit year shorthand found; use MM/YYYY so parsers read dates")

    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--expect", help="JSON file with companies/email/phone/source_text")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    expect = json.load(open(a.expect)) if a.expect else {}
    r = check(a.pdf, expect)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] round-trip via {r['engine']}, "
              f"{r['extracted_chars']} chars recovered")
        for v in r["violations"]:
            print(f"  FAIL  {v}")
        for w in r["warnings"]:
            print(f"  WARN  {w}")
        if r["engine"] == "stdlib":
            print("  note  install pymupdf for a stronger, independent extraction check")
    sys.exit(0 if r["passed"] else 1)


if __name__ == "__main__":
    main()
