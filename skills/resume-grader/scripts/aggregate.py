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


def _score_of(d):
    """A dimension may arrive as {"score": 88} or as a bare 88. Accept both; return
    None for anything that is not a usable number (booleans are not numbers here)."""
    if isinstance(d, dict):
        d = d.get("score")
    if isinstance(d, bool):
        return None
    if isinstance(d, (int, float)):
        return float(d)
    if isinstance(d, str):
        try:
            return float(d.strip())
        except ValueError:
            return None
    return None


def composite(dims):
    total, wsum = 0.0, 0
    for key, w in DIMENSION_WEIGHTS.items():
        s = _score_of(dims.get(key))
        if s is not None:
            total += max(0, min(100, s)) * w
            wsum += w
    # Divide by the FULL rubric weight, never by whatever happened to be present --
    # renormalizing would let a persona scored on one dimension report that single
    # score as its composite. aggregate() rejects partial panels before we get here;
    # this is the second line of defence for library callers.
    full = sum(DIMENSION_WEIGHTS.values())
    return round(total / full, 1) if wsum == full else (round(total / wsum, 1) if wsum else 0.0)


class IncompletePanel(ValueError):
    """A persona is missing or unscored. Never average around it."""


def aggregate(payload):
    company = payload.get("company", "")
    personas = payload.get("personas", {})
    if not isinstance(personas, dict):
        raise IncompletePanel("`personas` is missing or is not an object")

    # A missing persona must NEVER be silently scored 0 -- that averages a real
    # panel down and reports a confidently wrong number (one persona at 90 with two
    # missing would read as 30/100, "fail"). An incomplete panel is not a low score,
    # it is a failed grading run, and the caller has to know the difference.
    missing = []
    for p in PANEL:
        pd = personas.get(p)
        if not isinstance(pd, dict):
            missing.append(f"{p} (absent)")
            continue
        dims = pd.get("dimensions")
        if not isinstance(dims, dict):
            missing.append(f"{p} (no dimensions)")
            continue
        # Every one of the five must be scored. Scoring a persona on a subset and
        # renormalizing the weights silently reports the average of whatever showed
        # up as though it were the full rubric.
        absent = [k for k in DIMENSION_WEIGHTS if _score_of(dims.get(k)) is None]
        if absent:
            missing.append(f"{p} (missing dimension{'s' if len(absent) > 1 else ''}: {', '.join(absent)})")
    if missing:
        raise IncompletePanel(
            "incomplete panel - " + ", ".join(missing) +
            ". All three personas must be scored. Re-run the grading step; do not "
            "publish a partial panel as a score.")

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


USAGE = """usage: aggregate.py [panel.json]

Aggregate a 3-persona grading panel into a final score. Reads the panel JSON from
the given file, or from stdin if no file is given.

  python3 aggregate.py panel.json
  python3 aggregate.py < panel.json

Applies vote-coupling (a would-interview persona floors at 85) and the tiered pass
bar (reach employers need a majority interview vote AND panel_avg >= 90; everyone
else needs panel_avg >= 70). Prints the result as JSON."""

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    try:
        src = open(args[0]) if args else sys.stdin
    except OSError as e:
        print(f"cannot read {args[0]}: {e}\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.load(src)
    except json.JSONDecodeError as e:
        print(f"that is not valid JSON: {e}\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    try:
        print(json.dumps(aggregate(data), indent=2))
    except IncompletePanel as e:
        print(f"{e}", file=sys.stderr)
        sys.exit(3)
    except (KeyError, TypeError, AttributeError) as e:
        print(f"the panel JSON is missing something aggregate.py needs: {e}\n"
              f"Expected {{'company': ..., 'personas': {{hiring_manager, recruiter, ai_systems_rep}}}},\n"
              f"each with five scored dimensions and a would_interview vote.\n\n{USAGE}", file=sys.stderr)
        sys.exit(2)
