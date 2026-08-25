---
name: recruit-copilot
description: >
  The full job-search methodology: build an experience bank from resumes the user already
  has, define the search, pull and score open roles, tailor one resume per posting, prove a
  machine can still read it, grade it with a three-persona panel, apply the submit tier, and
  record what actually happened. Triggers on job search, job posting, resume, CV, ATS, tailor,
  apply, application, interview, offer, rejection, experience bank, recruiter.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, AskUserQuestion
methodology_version: 1.0.0
---

# Recruit Copilot

A job search is not a content problem. It is a **verification** problem: almost every failure
happens after you hit send, in machinery you cannot see, and none of it reports back. This
methodology is the set of checks that move those failures earlier, where they are still cheap.

Each numbered file below is one stage. Each is written to be executed with no other context:
read the file, run the stage, act on what it says. You do not need to read them in order to run
one of them, and you do not need this router to understand any of them.

## The loop

```
   01 intake ──▶ 02 goals ──▶ 03 scout ──▶ 04 tailor ──▶ 05 grade
                    ▲                                        │
                    │                                        ▼
                08 outcome ◀── 07 apply ◀────────── 06 submit-tier
```

It closes. Stage 08 is not a postscript: it is the only stage that produces evidence about
whether stages 03 through 06 are calibrated for the person running them. A loop with no
outcome record is a loop that cannot be wrong, which means it cannot be right either.

## The stages

| File | Stage | What it decides |
|---|---|---|
| [`01-intake.md`](01-intake.md) | Intake | What is true about this person, in one bank every resume draws from |
| [`02-goals.md`](02-goals.md) | Goals | What counts as a job worth their attention |
| [`03-scout.md`](03-scout.md) | Scout | Which open roles clear that bar, and why |
| [`04-tailor.md`](04-tailor.md) | Tailor | What goes on the page, and whether a machine can read the page |
| [`05-grade.md`](05-grade.md) | Grade | Whether three independent judges would advance it |
| [`06-submit-tier.md`](06-submit-tier.md) | Submit tier | What this employer costs to get wrong, and what bar that sets |
| [`07-apply.md`](07-apply.md) | Apply | The handoff to the human, and the record of what was sent |
| [`08-outcome.md`](08-outcome.md) | Outcome | What actually happened, and what that should change |

## The reference

| File | Purpose |
|---|---|
| [`09-invariants.md`](09-invariants.md) | The five mechanisms this repo has that others do not, the reasoning behind each threshold, and exactly how to retune them for your own search |

## Running a stage

Every stage names its own commands. Two variables appear throughout:

- `${CLAUDE_PLUGIN_ROOT:-.}` — the code. Set for you on a plugin install; falls back to `.`
  when someone has forked the repo and is working inside it. Both paths run the same scripts.
- `${RECRUIT_HOME:-$HOME/.recruit-copilot}` — the workspace. Everything the user creates lives
  here, deliberately outside the repo, so `git pull` can never touch their career history and
  a fork can never accidentally publish it.

The shipped Python is deterministic only. It reads files, renders the PDF, measures the page,
extracts the text back out, and does the panel arithmetic. Every judgement call (what to keep
from a bank, which bullets a posting is actually asking for, what a persona thinks) is made by
the model reading these files. That split is the point: **the model decides, the script counts.**

## The invariants

Enforced in code, not promised in marketing. Full reasoning in
[`09-invariants.md`](09-invariants.md).

1. **It does not submit to the companies that matter.** No submit path exists in this repo. The
   tier system in stage 06 is why that is a design position and not a missing feature.
2. **It cannot invent.** Every line on a resume traces to a bank entry the user confirmed.
3. **A resume a machine cannot read is never handed over as finished.** The round-trip gate is
   a hard gate, not a warning.
4. **Scoring is the user's.** No target titles, comp floors, or pass bars are baked in as silent
   defaults. With no goals file, the scout stops rather than scoring someone's career against a
   stranger's.
5. **The data stays on the machine.** The only network calls are to public job boards. Nothing
   is uploaded, and nothing phones home, including stage 08.

## Quick commands

These wrap the stages. A user may also just ask for a stage in words.

```
/recruit:intake      01   build the experience bank
/recruit:goals       02   set the search
/recruit:scout       03   pull and score open roles
/recruit:tailor      04   build a resume for one posting, run both gates
/recruit:grade       05   the three-persona panel
/recruit:outcome     08   record what happened
/recruit:dashboard        the local view of all of it
```

Stages 06 and 07 have no command on purpose. They are decisions, not scripts.
