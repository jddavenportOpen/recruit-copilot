# Running this without Claude Code

This repo ships as a Claude Code plugin, but **nothing in the pipeline requires Claude Code.**
The two scripts that produce every number are plain Python with **zero third-party imports**,
and the three judges are plain prompts you can hand to any model.

If you are an autonomous agent, a CI job, or a person with a terminal, this page is the whole
contract.

## What you need

- `python3` (3.8+). **No pip install. No virtualenv. No API key for the build half.**
- A model you can prompt, for the grading half. Any model. It does not have to be Claude.

Verify the fork before you trust it:

```bash
git clone https://github.com/jddavenportOpen/recruit-copilot.git
cd recruit-copilot
python3 smoke_test.py        # 40 checks, ~10s, exits non-zero on any failure
```

If that does not print `40/40 checks passed`, stop. Do not run the pipeline on real data
until it does.

## The loop, in three commands

### 1. Build — renders the PDF and runs both machine gates

```bash
python3 skills/resume-builder/scripts/build.py demo/tailored.json --out out.pdf --pages 1 --json
```

Input is one JSON file describing the resume (see `schema/experience-bank.schema.json` and
`demo/tailored.json` for a complete worked example). It returns `"passed": true|false` plus the
violations. Two gates run here and **both are mechanical, not opinions**:

- the **layout gate** measures the rendered page from real glyph bounding boxes, which is the
  only way to catch text printing on top of other text — that extracts as clean, correct,
  correctly-ordered text and no parser can see it;
- the **round-trip gate** re-opens the finished PDF, extracts the text, and diffs it against
  what was laid out. It hard-fails if the contact line did not survive.

A resume that fails either gate is not "a bit worse." It is a file that arrives blank or
garbled at an employer with no bounce and no error, so you never learn it happened.

### 2. Judge — three prompts, your model, run them separately

The three judge prompts are `agents/grader-recruiter.md`, `agents/grader-hiring-manager.md`
and `agents/grader-ai-systems-rep.md`. Strip the YAML frontmatter; the body is the system
prompt. Give each one the resume text and the job description, **in three separate calls with
no shared context** — they are meant to be independent seats, and letting them see each other
collapses the panel into one opinion wearing three hats.

Each must return, for its own persona:

- a `score` 0-100 on each of five dimensions, and
- a `would_interview` boolean with a one-line `reason`.

**Do not let the model compute the panel average.** That is step 3, and the separation is the
whole calibration.

### 3. Aggregate — deterministic arithmetic, no model involved

```bash
python3 skills/resume-grader/scripts/aggregate.py panel.json     # or pipe on stdin
```

`panel.json` is exactly this shape (`demo/panel.json` is a working example):

```json
{
  "company": "Anthropic",
  "personas": {
    "hiring_manager": {"dimensions": {"quantified_impact_credibility": {"score": 92}, "...": {}},
                       "would_interview": true, "reason": "..."},
    "recruiter":      {"...": {}},
    "ai_systems_rep": {"...": {}}
  }
}
```

The five dimension keys and their weights are at the top of `aggregate.py`. It returns
`panel_avg`, `interview_votes`, the per-persona scores, the threshold that applied, and
`overall_pass`.

Three mechanics live in that script rather than in a prompt, on purpose:

| | |
|---|---|
| **Vote-coupling** | a persona voting "would interview" cannot sit below 85, so mid-band compression cannot sink a genuine yes |
| **Tiered pass** | a reach employer needs a majority interview vote **and** panel >= 90; everyone else needs >= 70 |
| **Outcome anchoring** | the scale is defined in the prompts, not inferred by the model |

Why arithmetic instead of asking the model for a number: LLM judges cluster in the 55-72 band
and will vote "yes, interview" while scoring 72. Hand-averaging one real panel read **88.3**
where a naive aggregator returned **80.1**. A score that drifts out of sync with its own
verdict is not a measurement.

## The data boundary — read this before you point it at anyone's real history

This repo contains **no personal data**, by design, and the person running it supplies all of
it. If you are an agent operating on someone's behalf, that distinction is the whole safety
model:

- The **experience bank** is the operator's real career history. It is the only thing standing
  between a resume and a fabricated number. Treat it as the operator's data, not yours.
- **Every line on a generated resume must trace to a bank entry the operator confirmed.** The
  pipeline cannot invent, and you must not fill a gap with something plausible. A resume that
  overstates a figure does not fail loudly — it converts, gets checked later, and costs the
  offer.
- **There is no submit path in this repo, for any employer, behind any flag.** That is
  deliberate and it is argued in full in
  [`06-submit-tier.md`](.claude/skills/recruit-copilot/06-submit-tier.md). Build the file,
  report where it is, and let a human apply.
- Nothing here phones home. The only network calls in the wider toolkit are to public job
  boards.

## What the numbers are and are not

Every threshold in this repo — 90 for a reach employer, 70 for everyone else, 85 for the vote
floor — is a **reasoned judgement, not a measured one**. There is no funnel data behind them
yet. `outcomes/README.md` is where that accumulates, publicly, starting at zero. If you record
outcomes, record the ones that went badly too; a bar nobody has falsified is decoration.

## The rest of the methodology

`.claude/skills/recruit-copilot/` carries the reasoning for each stage — intake, goals, scout,
tailor, grade, submit tier, apply, outcome, and the five invariants. Those are readable as
plain markdown whatever is running them.
