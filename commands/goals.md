---
description: Set the search goals that drive job matching and the dashboard.
---

Set up or revise the user's search goals in
`${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/goals.json`.

This file does two jobs: the `goals` list is what the Goals tab tracks, and the
`search` block is what every job in the Jobs tab is scored against. Getting it right
is the difference between a search and a feed.

Ask for, and write into `search`:
- `titles.strong` - the titles they actually want. Required; without it every job
  scores the same.
- `titles.medium` - adjacent titles worth seeing.
- `seniority.prefer` / `seniority.avoid` - level words that should lift or sink a role.
- `comp_min` - a number, or 0 to ignore pay. Postings that state no pay are never
  penalized for it, because an unstated salary is not a failed one.
- `locations` - cities, "remote", "united states".
- `keywords_bonus` - domain words that make a role more interesting.
- `min_match` - the score below which a role is not worth showing. 55 is a sane start.

Also ask what they are actually trying to achieve and write those as `goals` rows
(`goal`, `status`, optional `note`) so the dashboard tracks the search, not just the
listings.

Then run `/recruit:scout` and show them the top matches with the `why` for each, so
they can see whether the scoring reflects what they said. Tune and re-run if not.
