---
description: "Ingest and score target-company roles from public Greenhouse and Ashby boards, then write them to the Jobs tab."
---

Run the job scout to refresh matched roles for the Jobs tab.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/dashboard/job_scout.py
```

Two files drive this, and they do different jobs:

- **Which boards** — `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/target_companies.json`, rows of
  `{"name", "ats": "greenhouse"|"ashby", "token"}`. If the file is absent, a small built-in list of
  AI companies is used in memory; nothing is written, so the user still has to create the file to
  choose their own targets.
- **How roles score** — `state/goals.json` (from `/recruit:goals`): title keywords, seniority, comp
  floor, locations, and `min_match`. If it does not exist yet, the scout writes a starter file and
  **stops**, rather than scoring the user's career against somebody else's defaults. If that
  happens, walk them through `/recruit:goals` before re-running.

It pulls roles from the public Greenhouse boards-api and Ashby posting-api (both no-auth and
ToS-clean), scores them, enriches the top matches with comp where the posting lists it, and writes
`state/jobs.json`, which is what the Jobs tab reads.

After it runs, summarize for the user: how many roles matched, the top handful (company, title,
match score, comp), and which boards failed if any (the `sources` list carries a plain-language
reason per board). To change what counts as a match, send them to `/recruit:goals` — not to
`target_companies.json`, which only picks boards. For a stricter list, re-run with `--min 65`.
