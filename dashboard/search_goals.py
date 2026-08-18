#!/usr/bin/env python3
"""Turn your stated goals into the function that scores every job.

The Jobs tab is only worth opening if it reflects the search you are actually
running. Before this, scoring lived in hardcoded keyword lists, which meant every
person who installed this inherited the author's job hunt: his target titles, his
comp floor, his idea of senior. That is a feed, not a search.

Now one file, workspace/state/goals.json, holds both the goals the dashboard
tracks and the `search` block that drives matching. Change what you want and the
Jobs tab changes with it.

    {
      "search": {
        "titles":   {"strong": [...], "medium": [...]},
        "seniority":{"prefer": [...], "avoid": [...]},
        "comp_min": 180000,
        "locations": ["remote", "united states"],
        "keywords_bonus": ["ai", "llm"],
        "min_match": 55
      },
      "goals": [ ... ]
    }
"""

from __future__ import annotations

import json
import os
import re

# Used only to write the starter file. These are an EXAMPLE, never a silent
# default: scoring a stranger's career against them would quietly hand them
# somebody else's job search.
EXAMPLE_SEARCH = {
    "titles": {
        "strong": ["product manager", "senior product manager", "principal product manager"],
        "medium": ["program manager", "product owner", "technical product manager"],
    },
    "seniority": {"prefer": ["senior", "staff", "principal", "lead"],
                  "avoid": ["intern", "new grad", "early career", "apprentice"]},
    "comp_min": 0,
    "locations": ["remote", "united states"],
    "keywords_bonus": ["ai", "ml", "llm", "platform"],
    "min_match": 55,
}
EXAMPLE_GOALS = [
    {"goal": "Replace the hardcoded example with the titles you actually want",
     "status": "active",
     "note": "Everything in the Jobs tab is scored against the search block in this file."},
]

_PAY = re.compile(r"\$\s?(\d{2,3}),?(\d{3})\b")


class NoGoals(Exception):
    """Raised when there is no search block. The caller must stop and say so."""


def path_for(state_dir: str) -> str:
    return os.path.join(state_dir, "goals.json")


def write_starter(state_dir: str) -> str:
    os.makedirs(state_dir, exist_ok=True)
    p = path_for(state_dir)
    if not os.path.exists(p):
        with open(p, "w") as f:
            json.dump({"search": EXAMPLE_SEARCH, "goals": EXAMPLE_GOALS}, f, indent=2)
    return p


def load(state_dir: str) -> dict:
    p = path_for(state_dir)
    if not os.path.exists(p):
        write_starter(state_dir)
        raise NoGoals(
            f"no goals yet, so there is nothing to match against. A starter file is now at\n"
            f"  {p}\n"
            f"Put your real target titles, comp floor and locations in the `search` block, "
            f"then run the scout again. Or run /recruit:goals and answer a few questions.")
    with open(p) as f:
        data = json.load(f)
    search = data.get("search")
    if not search or not (search.get("titles", {}).get("strong")):
        raise NoGoals(
            f"{p} has no `search.titles.strong`, so every job would score the same.\n"
            f"List the titles you actually want, then run the scout again.")
    merged = dict(EXAMPLE_SEARCH)
    merged.update(search)
    merged["titles"] = {**EXAMPLE_SEARCH["titles"], **search.get("titles", {})}
    merged["seniority"] = {**EXAMPLE_SEARCH["seniority"], **search.get("seniority", {})}
    return merged


def comp_meets(text: str, floor: int) -> bool | None:
    """True/False if a figure is posted, None if the posting does not say.
    An unstated salary is not a failed one, so it must not be scored as though
    the job pays nothing."""
    if not floor:
        return None
    best = None
    for m in _PAY.finditer(text or ""):
        val = int(m.group(1) + m.group(2))
        if val >= 20000:                       # below this it is an hourly rate or a typo
            best = max(best or 0, val)
    if best is None:
        return None
    return best >= floor


def score(title: str, location: str, search: dict, jd_text: str = "") -> tuple[int, list[str]]:
    """Return (0-100, reasons). Reasons make the Jobs tab explainable instead of
    a number you have to trust."""
    t = (title or "").lower()
    reasons = []

    strong = [k.lower() for k in search["titles"].get("strong", [])]
    medium = [k.lower() for k in search["titles"].get("medium", [])]

    hit = next((k for k in strong if k in t), None)
    if hit:
        s = 78; reasons.append(f"title matches a target: {hit!r}")
    else:
        hit = next((k for k in medium if k in t), None)
        if hit:
            s = 58; reasons.append(f"title is adjacent: {hit!r}")
        else:
            head = [w for w in re.findall(r"[a-z]+", " ".join(strong)) if len(w) > 3]
            if any(w in t for w in head):
                s = 36; reasons.append("partial title overlap only")
            else:
                s = 10; reasons.append("title does not match anything you asked for")

    prefer = [k.lower() for k in search["seniority"].get("prefer", [])]
    avoid = [k.lower() for k in search["seniority"].get("avoid", [])]
    if any(k in t for k in prefer):
        s += 12; reasons.append("at or above your target level")
    if any(k in t for k in avoid):
        s -= 30; reasons.append("below the level you asked for")

    for k in (x.lower() for x in search.get("keywords_bonus", [])):
        if re.search(rf"\b{re.escape(k)}\b", t):
            s += 5; reasons.append(f"bonus keyword {k!r}")
            break

    loc = (location or "").lower()
    locs = [x.lower() for x in search.get("locations", [])]
    if locs:
        if any(k in loc for k in locs):
            s += 3; reasons.append("location works for you")
        elif loc:
            s -= 8; reasons.append(f"location {location!r} is not on your list")

    floor = int(search.get("comp_min") or 0)
    if floor and jd_text:
        ok = comp_meets(jd_text, floor)
        if ok is True:
            s += 6; reasons.append(f"posted pay clears your ${floor:,} floor")
        elif ok is False:
            s -= 25; reasons.append(f"posted pay is under your ${floor:,} floor")
        else:
            reasons.append("no pay posted, so pay was not scored")

    return max(0, min(100, s)), reasons
