---
description: Ingest and score target-company roles from public ATS boards, then write them to the Jobs tab.
---

Run the job scout to refresh matched roles for the Jobs tab.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/dashboard/job_scout.py
```

This reads `${RECRUIT_HOME:-$CLAUDE_PLUGIN_ROOT/workspace}/state/target_companies.json` (creating a
default if absent), pulls each company's roles from the public Greenhouse boards-api (ToS-clean, no
auth), scores them against the user's criteria and title keywords, enriches the top matches with
comp where the posting lists it, and writes `state/jobs.json`.

After it runs, summarize for the user: how many roles matched, the top handful (company, title,
match score, comp), and remind them they can edit `target_companies.json` to change target boards
or the title keywords that define a match. If they want a stricter list, re-run with `--min 65`.
