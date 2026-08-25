# 05 — Grade

**Goal of this stage:** three independent reads of the finished resume against this specific
posting, and one number that did not come from the model's own arithmetic.

**Done when:** `aggregate.py` has printed a result, and the numbers you report are the ones it
printed.

---

## Why a panel, and why these three

A single judge scoring "is this a good resume" answers a question nobody is actually asking. A
real application is read three times by three readers with incompatible criteria, and it can die
at any one of them:

| Persona | The question | Kills you by |
|---|---|---|
| `recruiter` | Six-second skim: does this obviously clear the bar? | Level mismatch, missing keywords, no instant yes |
| `hiring_manager` | Can this person do the job on day one? | Depth, credibility, whether the numbers are believable |
| `ai_systems_rep` | The ATS and AI screener, the machine gate before any human | Parse failure, a missing must-have, a knockout criterion |

The third seat is the one usually left out and it is the one most applications actually hit
first. Its `reason` field must name the specific missing keyword or knockout, not offer a general
impression.

**Run them as three parallel subagents when you can.** This repo ships one agent definition per
seat: `grader-recruiter`, `grader-hiring-manager`, `grader-ai-systems-rep`. Judges that cannot
see each other's scores do not anchor on each other, and anchoring is the failure that makes a
panel worthless. Scoring all three in one pass is the supported fallback and produces the same
JSON.

## The five dimensions

Keys must match exactly. The weights live in `aggregate.py`:

| Dimension | Weight | Asks |
|---|---|---|
| `quantified_impact_credibility` | 25 | Specific, quantified, believable? |
| `experience_domain_relevance` | 25 | Relevant to *this* role? |
| `keyword_requirement_coverage` | 20 | Covers the posting's stated requirements and language? |
| `target_employer_convention_fit` | 15 | Fits this employer's level and conventions? |
| `structure_clarity_execution` | 15 | Clear, ATS-safe, free of AI tells? |

Impact and relevance carry half the weight between them because they are the two a human reader
cannot be talked out of.

## The outcome-anchored scale

This is the calibration. Do not treat it as a rubric footnote.

```
90-100   strong yes, top 5 percent of the stack
85-89    would interview
70-84    borderline
55-69    likely no
40-54    weak
 0-39    reject
```

**A band is a decision, not an adjective.** If you would spend real interview time on this
candidate, the persona's dimensions land at 85 or above. Use the full range. Set
`would_interview` true only if you would actually give up the hour.

## Output shape

```json
{
  "company": "<employer name, exactly as they write it>",
  "personas": {
    "hiring_manager": {
      "dimensions": {
        "quantified_impact_credibility": {"score": 88},
        "keyword_requirement_coverage": {"score": 84},
        "experience_domain_relevance": {"score": 90},
        "target_employer_convention_fit": {"score": 82},
        "structure_clarity_execution": {"score": 86}
      },
      "would_interview": true,
      "reason": "<one line: the deciding factor>"
    },
    "recruiter": {},
    "ai_systems_rep": {}
  }
}
```

The `company` field is not cosmetic. Stage 06 reads it to pick the pass bar.

## Aggregate — and never do this arithmetic yourself

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/skills/resume-grader/scripts/aggregate.py \
    "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/panel.json
```

The script applies two corrections a mental average silently skips, then the tiered bar from
stage 06. Measured on a real resume: hand-averaging the same panel reported **88.3** where the
aggregator returned **80.1**: a clear pass and a clear fail, from identical inputs.

**Vote-coupling.** A persona that voted "would interview" cannot sit below 85; its composite is
floored there. This exists because LLM judges routinely vote yes and then score a 72 — the
verdict and the number come from different parts of the reasoning and they drift apart. Coupling
them means a genuine yes cannot be sunk by residual mid-band compression.

**Incomplete panels are a failed run, not a low score.** If a persona is missing, or any one of
its five dimensions is unscored, `aggregate.py` exits 3 and refuses. It never averages around a
gap: one persona at 90 with two missing would otherwise read as 30/100 and look like a confident
verdict. Re-run the grading; do not publish a partial panel.

**Report only what the script printed.** `panel_avg`, `raw_panel_avg`, `interview_votes`,
`overall_pass`, `threshold`, `weakest_persona` and the per-persona scores come from its output,
verbatim. If you cannot run it (no Bash, missing script, non-zero exit), say plainly that the
panel could not be aggregated, show the raw per-persona JSON, and stop. A resume with no score is
a normal outcome. A number that was never aggregated is a wrong answer wearing the costume of a
right one.

## Reporting it

Lead with `weakest_persona` and its reason. That is the actionable sentence: it names the seat
that would have rejected the application and why. Then the panel average against the threshold,
then the vote count.

Report a fail as a fail. A grader that says every resume is good is worth nothing, and the user
can tell.

Next: [`06-submit-tier.md`](06-submit-tier.md).
