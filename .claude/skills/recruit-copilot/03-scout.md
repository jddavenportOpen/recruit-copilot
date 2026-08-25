# 03 — Scout

**Goal of this stage:** turn a list of employers the user cares about into a scored, explained
shortlist of roles that are actually open.

**Done when:** `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/jobs.json` holds scored roles, and
the user can see the reasons behind any score without asking.

---

## Why it pulls from ATS endpoints and not from a job site

Greenhouse and Ashby both publish the same board a company's careers page renders, as public
JSON, no auth:

```
https://boards-api.greenhouse.io/v1/boards/{token}/jobs
https://api.ashbyhq.com/posting-api/job-board/{org}
```

Three consequences worth understanding, because they define what this stage can and cannot do:

1. **It is the employer's own data.** No aggregator lag, no reposted ghost listing, no scraping
   a site whose terms forbid it. What comes back is what their recruiting team published.
2. **Coverage is by company, not by keyword.** You cannot ask this "what AI jobs exist"; you ask
   it "what is open at these twenty employers." That is a real limitation and it is also the
   better question, because a job search that starts from a keyword ends at whoever bought the ad.
3. **Other ATS platforms are not wired.** Lever, Workday, SmartRecruiters and the rest are not
   supported. Say so rather than silently returning a short list.

Greenhouse ships the posting body as **HTML-escaped HTML**, so unescaping has to happen before
tag-stripping — `job_scout.py` handles this, and the bug it fixes is worth knowing about: before
it, every Greenhouse posting reached the tailoring and grading stages as a wall of `div`, `h2`,
`li` and `strong`, and those stages were matching the user's keywords against markup.

## Procedure

**1. Set the boards.** `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/target_companies.json`,
one row per employer:

```json
[{"name": "Example Corp", "ats": "greenhouse", "token": "examplecorp"}]
```

The `token` is the company's board slug — the last path segment of their Greenhouse or Ashby
careers URL. If the file is absent, a small built-in list of AI companies is used **in memory
only**; nothing is written, so the user still has to create the file to make the target list
theirs. Do not let them skip this: the target list is half the search.

**2. Run it.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/dashboard/job_scout.py
```

If there is no goals file, this stops with an error and writes a starter. That is stage 02's
refusal doing its job. Walk them through `02-goals.md` and re-run; do not work around it.

**3. Read the scores back as reasons, not as numbers.**

Every score arrives with the list of reasons that produced it. Report those, not the integer. "84
— title matches a target: 'staff engineer', at or above your target level, location works for
you" is a claim a person can disagree with. "84" is a number they have to trust, and trusting an
unexplained number is exactly the habit this repo is trying to break.

The scoring is entirely from the user's own `search` block. There are no employer-quality
weights, no hidden preferences, and no ranking the user did not write.

## How a score is built

Starting base, from the title only:

| Condition | Base |
|---|---|
| Title contains a `titles.strong` entry | 78 |
| Title contains a `titles.medium` entry | 58 |
| Title shares a significant word with a strong entry | 36 |
| Nothing matches | 10 |

Then adjustments: `seniority.prefer` +12, `seniority.avoid` −30, a `keywords_bonus` hit +5 (once),
a location match +3, a stated location that is not on the list −8, posted pay clearing `comp_min`
+6, posted pay below it −25, no posted pay 0 and a note saying so. Clamped to 0–100.

Anything at or above `min_match` (default 55) is kept; the top N per company are selected and
their full posting text is fetched for stage 04.

## What to do with the shortlist

Do not hand over twenty roles. Pick the three or four with the best reasons, say why, and take
one into stage 04. Volume is the failure mode this whole repo exists to correct. The scout
exists to make a short list defensible, not to make a long one possible.

Next: [`04-tailor.md`](04-tailor.md).
