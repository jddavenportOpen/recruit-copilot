#!/usr/bin/env python3
"""Check an experience bank before anything is built from it.

The bank is the only thing a resume is allowed to draw from, so a defect here is
a defect on every resume the tool will ever produce. This catches the ones that
are checkable without knowing your career: structural faults, duplicate ids,
dates that will not parse, overlapping employment the model will happily put on
one page, and bullets that no tailoring can save.

What it deliberately does NOT do is judge whether a claim is true. Only you can
do that, and pretending otherwise would be the exact dishonesty this tool exists
to avoid.

Exit 0 clean, 1 problems found, 2 unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter

MIN_BULLET_WORDS = 6
MAX_BULLET_CHARS = 240
WEAK_OPENERS = {"responsible", "helped", "worked", "assisted", "participated",
                "involved", "tasked", "duties"}
FILLER = ("synergy", "leverage", "utilize", "spearhead", "world-class",
          "results-driven", "team player", "go-getter", "thought leader")
MONTH_NUM = r"(?:0?[1-9]|1[0-2])"
MONTH_NAME = (r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*")
_TERM = rf"(?:(?:{MONTH_NUM}[/\-]|{MONTH_NAME}\.?\s+)?\d{{4}}|present|current|now)"
DATE_RE = re.compile(rf"^\s*{_TERM}\s*(?:to|through|-|–|—)\s*{_TERM}\s*$", re.I)
# Real banks disagree about this key. Read every spelling rather than making the
# user rename their data to match ours.
DATE_KEYS = ("dates", "date", "period", "range")


def job_dates(job: dict) -> str:
    for k in DATE_KEYS:
        v = job.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    start, end = job.get("start"), job.get("end")
    if start:
        return f"{start} to {end or 'Present'}"
    return ""


def _year(token: str) -> int | None:
    m = re.search(r"(\d{4})", token or "")
    return int(m.group(1)) if m else None


def validate(bank: dict) -> dict:
    errors, warnings, notes = [], [], []

    def err(m): errors.append(m)
    def warn(m): warnings.append(m)

    jobs = bank.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        err("no jobs in the bank; a resume cannot be built from nothing")
        return _result(errors, warnings, notes, {})

    ids = Counter(j.get("id", "") for j in jobs)
    for jid, n in ids.items():
        if n > 1:
            err(f"job id {jid!r} appears {n} times; ids must be unique")
        if not jid:
            err("a job has no id")

    total_bullets = 0
    spans = []
    for j in jobs:
        label = f"{j.get('company', '?')} / {j.get('title', '?')}"
        for field in ("title", "company"):
            if not j.get(field):
                err(f"{label}: missing {field}")

        dates = job_dates(j)
        if not dates:
            warn(f"{label}: no dates; recruiters read the timeline first")
        elif not DATE_RE.match(dates):
            warn(f"{label}: dates {dates!r} are not in a form parsers read reliably; "
                 "prefer MM/YYYY to MM/YYYY or 'Present'")
        else:
            parts = re.split(r"\s*(?:to|through|-|–|—)\s*", dates, maxsplit=1)
            start = _year(parts[0])
            end = None if re.search(r"present|current", parts[-1], re.I) else _year(parts[-1])
            if start:
                spans.append((start, end, label))

        bullets = j.get("bullets")
        if not isinstance(bullets, dict) or not bullets:
            err(f"{label}: no bullets; this job can never appear on a resume")
            continue
        total_bullets += len(bullets)

        for bid, text in bullets.items():
            if not isinstance(text, str) or not text.strip():
                err(f"{label}: bullet {bid!r} is empty")
                continue
            words = text.split()
            if len(words) < MIN_BULLET_WORDS:
                warn(f"{label}/{bid}: only {len(words)} words; too thin to carry a line")
            if len(text) > MAX_BULLET_CHARS:
                warn(f"{label}/{bid}: {len(text)} characters; it will run three lines "
                     "on the page, split it or cut it")
            if words and words[0].lower().rstrip(",.") in WEAK_OPENERS:
                warn(f"{label}/{bid}: opens with {words[0]!r}; lead with what changed")
            low = text.lower()
            for f in FILLER:
                if f in low:
                    warn(f"{label}/{bid}: contains {f!r}, which reads as filler")
            if not re.search(r"\d", text):
                notes.append(f"{label}/{bid}: no number in this bullet")

        req = j.get("required_bullets") or []
        missing = [r for r in req if r not in bullets]
        if missing:
            err(f"{label}: required_bullets names ids that do not exist: {', '.join(missing)}")

    # overlapping employment, which quietly produces an unexplainable timeline
    dated = [s for s in spans if s[0]]
    for i, (s1, e1, l1) in enumerate(dated):
        for s2, e2, l2 in dated[i + 1:]:
            end1, end2 = e1 or 9999, e2 or 9999
            if s1 < end2 and s2 < end1 and not (e1 is None and e2 is None):
                warn(f"overlapping dates: {l1} and {l2}. Fine if both are real, but never "
                     "put both on one resume without a line explaining it")

    summaries = bank.get("summaries") or {}
    if not summaries:
        warn("no summaries; the tailoring step has nothing to pick from")
    elif len(summaries) < 2:
        notes.append("only one summary; add one per kind of role you target")

    if not (bank.get("skills_pool") or {}):
        warn("no skills_pool; the skills section will be empty")

    # contact may legitimately arrive as the schema object or, from a hand-edited
    # bank, as the flat "email | phone | location" string the renderer uses. Either
    # way there must be a reachable email, or the round-trip gate will hard-fail.
    contact = bank.get("contact") or {}
    if isinstance(contact, dict):
        if not contact.get("email"):
            err("no contact email; the resume will fail the round-trip check")
        if not contact.get("phone"):
            warn("no contact phone")
    elif isinstance(contact, str):
        if not re.search(r"[\w.+\-]+@[\w\-]+\.\w{2,}", contact):
            err("no contact email; the resume will fail the round-trip check")
        if not re.search(r"\d{3}\D*\d{3}\D*\d{4}", contact):
            warn("no contact phone")
    else:
        err("contact must be an object with an email (or a string containing one)")

    stats = {"jobs": len(jobs), "bullets": total_bullets,
             "summaries": len(summaries), "skill_groups": len(bank.get("skills_pool") or {})}
    if total_bullets < len(jobs) * 3:
        warn(f"only {total_bullets} bullets across {len(jobs)} jobs; the bank should be far "
             "deeper than any single resume so tailoring has real choices")
    return _result(errors, warnings, notes, stats)


def _result(errors, warnings, notes, stats):
    return {"passed": not errors, "errors": errors, "warnings": warnings,
            "notes": notes, "stats": stats}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bank", nargs="?", default="workspace/master-experience.json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        bank = json.load(open(a.bank))
    except Exception as e:
        print(f"could not read {a.bank}: {e}", file=sys.stderr)
        sys.exit(2)

    r = validate(bank)
    if a.json:
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["passed"] else 1)

    s = r["stats"]
    print(f"[{'PASS' if r['passed'] else 'FAIL'}] {s.get('jobs',0)} jobs, {s.get('bullets',0)} bullets, "
          f"{s.get('summaries',0)} summaries, {s.get('skill_groups',0)} skill groups")
    for e in r["errors"]:
        print(f"  ERROR {e}")
    for w in r["warnings"]:
        print(f"  WARN  {w}")
    for n in r["notes"][:8]:
        print(f"  note  {n}")
    if len(r["notes"]) > 8:
        print(f"  note  ... and {len(r['notes']) - 8} more")
    sys.exit(0 if r["passed"] else 1)


if __name__ == "__main__":
    main()
