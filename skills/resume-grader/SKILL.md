---
name: resume-grader
description: Grade a resume against a specific job description with a calibrated 3-persona interview panel (Hiring Manager, Recruiter, AI Systems Rep), scoring in-session and aggregating deterministically. Use when the user asks to grade, score, or judge a resume against a job, or asks whether a resume would get an interview.
---

# Resume Grader (in-session, calibrated)

You are the grading panel. Claude scores the resume here in the session, so there is
no API key and no marginal cost. A Python script does the arithmetic so the numbers
never drift from the verdict.

## Inputs
- The resume text (extract from the PDF/Doc if needed).
- The job description text.
- The employer name (used for the tiered pass bar).

## Procedure

Grade the resume from THREE independent personas. For each persona, score these five
dimensions on the outcome-anchored 0-100 scale, then cast a would-interview vote.

**The five dimensions** (keys must match exactly):
- `quantified_impact_credibility` - are the accomplishments specific, quantified, and believable?
- `keyword_requirement_coverage` - does it cover the JD's stated requirements and language?
- `experience_domain_relevance` - is the experience actually relevant to THIS role?
- `target_employer_convention_fit` - does it fit this employer's level and conventions?
- `structure_clarity_execution` - is it well structured, clear, ATS-safe, and free of AI tells?

**The three personas** (be discriminating, calibrated to the anchors, not merely harsh):
- `hiring_manager` - can this person do the job on day one? Fit, credibility, depth.
- `recruiter` - the 6-second skim: level match, keyword coverage, obvious yes/no.
- `ai_systems_rep` - for technical roles, is this a real builder? Hard-to-fake signal, AI-tell detection.

**The outcome-anchored scale (critical - this is the calibration):**
- 90-100 = strong yes, top 5 percent of the stack.
- 85-89 = would interview.
- 70-84 = borderline.
- 55-69 = likely no.
- 40-54 = weak.
- 0-39 = reject.
A score band IS a decision. If you would interview this person, the persona's dimensions
should land at 85+. Do not compress everything into the 60-72 mid-band. Use the full range.

Set `would_interview` true only if you would spend real interview time on this candidate.

## Output, then aggregate

Emit one JSON object of this exact shape and write it to a temp file:

```json
{
  "company": "<employer>",
  "personas": {
    "hiring_manager": {"dimensions": {"quantified_impact_credibility": {"score": 88},
      "keyword_requirement_coverage": {"score": 84}, "experience_domain_relevance": {"score": 90},
      "target_employer_convention_fit": {"score": 82}, "structure_clarity_execution": {"score": 86}},
      "would_interview": true, "reason": "<one line: the deciding factor>"},
    "recruiter": { ... same shape ... },
    "ai_systems_rep": { ... same shape ... }
  }
}
```

Then run the deterministic aggregator (vote-coupling + tiered pass):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-grader/scripts/aggregate.py /tmp/panel.json
```

Report the returned `panel_avg`, `interview_votes`, `overall_pass`, per-persona scores, and
the `weakest_persona` with its reason. For a reach employer the bar is a majority interview
vote AND panel_avg >= 90; otherwise panel_avg >= 70.

## Honesty
Grade what is on the page. Never invent strengths the resume does not show. If the resume
makes a claim you cannot verify from its own content, treat it skeptically, do not reward it.
Separating a genuinely strong resume from a weak one is the whole job; do not inflate.
