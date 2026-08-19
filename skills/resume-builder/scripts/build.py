#!/usr/bin/env python3
"""Render a tailored resume and run both machine gates on it.

    render -> layout QA (measure the page) -> round-trip (extract it back out)

Gate order matters. Layout QA runs first because a page-overflow or a five-line
bullet is a content problem you fix by cutting words. The round-trip runs second
because it answers a different question: can a machine still read what you made.

Exit codes:
    0  both gates passed
    1  layout QA failed (fix the content, re-run)
    2  round-trip failed (the file is not reliably machine-readable)
    3  bad input

Usage:
    python3 build.py resume.json --out workspace/resumes/acme-pm.pdf --pages 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import format_qa            # noqa: E402
import parse_check          # noqa: E402
import render_resume        # noqa: E402


def build(resume: dict, out_path: str, target_pages: int | None = 1) -> dict:
    layout = render_resume.render(resume, out_path)
    qa = format_qa.analyze(layout, target_pages)

    expect = {
        "companies": [j.get("company", "") for j in resume.get("jobs", []) if j.get("company")],
        "source_text": render_resume.laid_out_text(layout),
    }
    contact = resume.get("contact", "")
    for key, pat in (("email", parse_check.CONTACT["email"]),
                     ("phone", parse_check.CONTACT["phone"])):
        import re
        m = re.search(pat, contact)
        if m:
            expect[key] = m.group(0)

    rt = parse_check.check(out_path, expect)
    return {"pdf": out_path, "pages": layout["pages"], "layout_qa": qa, "round_trip": rt,
            "passed": qa["passed"] and rt["passed"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("resume_json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        resume = json.load(open(a.resume_json))
    except Exception as e:
        print(f"could not read {a.resume_json}: {e}", file=sys.stderr)
        sys.exit(3)

    if not isinstance(resume, dict):
        print(f"{a.resume_json} should contain a JSON object describing one resume, "
              f"not a {type(resume).__name__}.", file=sys.stderr)
        sys.exit(3)
    try:
        r = build(resume, a.out, a.pages)
    except Exception as e:
        # Exit 3 is "bad input". Exiting 1 here would tell the caller the LAYOUT
        # failed, and they would go cut words to fix a malformed-JSON problem.
        print(f"could not render {a.resume_json}: {type(e).__name__}: {e}\n"
              f"Expected shape: {{name, contact, summary, jobs:[{{company,title,location,"
              f"dates,bullets:[...]}}], education:[...], skills:{{Category: 'a, b'}}}}",
              file=sys.stderr)
        sys.exit(3)

    if a.json:
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["passed"] else (1 if not r["layout_qa"]["passed"] else 2))

    qa, rt = r["layout_qa"], r["round_trip"]
    print(f"built {r['pdf']} ({r['pages']} page(s))\n")
    print(f"layout   [{'PASS' if qa['passed'] else 'FAIL'}] {qa['errors']} error(s), "
          f"{qa['warnings']} warning(s), {qa['stats']['bullets']} bullets, "
          f"longest {qa['stats']['max_bullet_lines']} lines")
    for i in qa["issues"]:
        print(f"   {i['level'].upper():5} {i['code']}: {i['detail']}")
    print(f"\nround-trip [{'PASS' if rt['passed'] else 'FAIL'}] via {rt['engine']}, "
          f"{rt['extracted_chars']} chars recovered")
    for v in rt["violations"]:
        print(f"   FAIL  {v}")
    for w in rt["warnings"]:
        print(f"   WARN  {w}")
    if rt["engine"] == "stdlib":
        print("   note  pip install pymupdf for an independent extraction engine")

    print()
    if r["passed"]:
        print("Both gates passed. This is safe to send. Grade it next: /recruit:grade")
        sys.exit(0)
    if not qa["passed"]:
        print("Layout gate failed. Cut words, then re-run.")
        sys.exit(1)
    print("Round-trip failed. A machine cannot reliably read this file. Do not send it.")
    sys.exit(2)


if __name__ == "__main__":
    main()
