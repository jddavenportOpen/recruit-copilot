#!/usr/bin/env python3
"""Deterministic aggregation for the calibrated 3-persona resume panel.

Claude scores the resume in-session (three personas, five dimensions each, plus a
would-interview vote); THIS script does the arithmetic, so the numbers are never
the model's own mental math. That separation is the calibration: it prevents the
score from drifting out of sync with the verdict.

Input (stdin or a file): JSON of the shape
  {
    "company": "Anthropic",
    "personas": {
      "hiring_manager": {"dimensions": {"<dim>": {"score": 0-100}, ...},
                         "would_interview": true, "reason": "..."},
      "recruiter":      {...},
      "ai_systems_rep": {...}
    }
  }

Output: the panel result with the vote-coupled, calibrated panel_avg.

The three calibration mechanics (documented in the README):
  1. Outcome-anchored scoring happens in the prompt (see resume-grader SKILL.md).
  2. Vote-coupling: a persona voting "would interview" cannot sit below 85, so
     residual mid-band compression can't sink a genuine yes (ADVANCE_FLOOR).
  3. Tiered pass: reach employers need a majority interview vote AND panel >= 90;
     everyone else needs panel >= 70.
"""
import json
import sys

DIMENSION_WEIGHTS = {
    "quantified_impact_credibility": 25,
    "keyword_requirement_coverage": 20,
    "experience_domain_relevance": 25,
    "target_employer_convention_fit": 15,
    "structure_clarity_execution": 15,
}
ADVANCE_FLOOR = 85
REACH_THRESHOLD = 90
DEFAULT_THRESHOLD = 70
PANEL = ("hiring_manager", "recruiter", "ai_systems_rep")
REACH = {"anthropic", "openai", "google", "google deepmind", "deepmind", "meta", "microsoft",
         "apple", "nvidia", "xai", "mistral", "cohere", "scale ai", "databricks", "stripe",
         "mckinsey", "bcg", "bain"}


def is_reach(company):
    c = (company or "").strip().lower()
    return any(c == r or c.startswith(r + " ") or c.startswith(r + ",") for r in REACH)


def composite(dims):
    total, wsum = 0.0, 0
    for key, w in DIMENSION_WEIGHTS.items():
        d = dims.get(key) or {}
        s = d.get("score")
        if isinstance(s, (int, float)):
            total += max(0, min(100, s)) * w
            wsum += w
    return round(total / wsum, 1) if wsum else 0.0


def aggregate(payload):
    company = payload.get("company", "")
    personas = payload.get("personas", {})
    scores, votes = {}, {}
    for p in PANEL:
        pd = personas.get(p) or {}
        scores[p] = composite(pd.get("dimensions") or {})
        votes[p] = bool(pd.get("would_interview"))
    raw = round(sum(scores.values()) / len(PANEL), 1)
    effective = [max(scores[p], ADVANCE_FLOOR) if votes[p] else scores[p] for p in PANEL]
    panel_avg = round(sum(effective) / len(PANEL), 1)
    interview_votes = sum(votes.values())
    threshold = REACH_THRESHOLD if is_reach(company) else DEFAULT_THRESHOLD
    if is_reach(company):
        passed = interview_votes >= 2 and panel_avg >= threshold
    else:
        passed = panel_avg >= threshold
    weakest = min(PANEL, key=lambda p: scores[p])
    return {
        "company": company, "is_reach": is_reach(company), "threshold": threshold,
        "panel_avg": panel_avg, "raw_panel_avg": raw, "interview_votes": interview_votes,
        "overall_pass": passed, "weakest_persona": weakest,
        "hiring_manager": scores["hiring_manager"], "recruiter": scores["recruiter"],
        "ai_systems_rep": scores["ai_systems_rep"],
        "panel": {p: {"score": scores[p], "would_interview": votes[p],
                      "reason": (personas.get(p) or {}).get("reason", "")} for p in PANEL},
    }


if __name__ == "__main__":
    src = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
    print(json.dumps(aggregate(json.load(src)), indent=2))
