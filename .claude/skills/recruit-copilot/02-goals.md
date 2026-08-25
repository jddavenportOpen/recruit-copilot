# 02 — Goals

**Goal of this stage:** write the file that turns "show me jobs" into "show me *these* jobs."

**Done when:** `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/goals.json` has a `search` block
with real `titles.strong` values in it, and the `_unedited_example` marker is gone.

---

## Why this is a stage and not a config file

The scoring function in stage 03 has to come from somewhere. Before this file existed, it came
from keyword lists written into the source, which meant every person who installed the tool
inherited the author's job hunt: his target titles, his comp floor, his idea of what "senior"
means. That is a feed. A feed is worse than nothing, because it looks like a search.

So the tool refuses to guess. `search_goals.py` ships an example block, writes it as a starter
file, and then **stops with an error** rather than scoring anyone against it. It detects the
untouched template two ways, a `_unedited_example` marker and a check on whether
`titles.strong` still equals the shipped example, because people edit the titles and leave the
marker behind, and telling someone their edited file is untouched is simply wrong.

That refusal is invariant 4. It costs a user ninety seconds and it is the difference between the
Jobs tab being their search and being someone else's.

## Procedure

Ask for each field below and write it into the `search` block. Ask in plain language; do not
read the user the JSON.

| Field | Ask | Why it matters |
|---|---|---|
| `titles.strong` | "What titles do you actually want?" | **Required.** Without it every job scores the same. A strong title hit sets the base score to 78. |
| `titles.medium` | "What adjacent titles are worth seeing?" | Base 58. This is where people find the role they did not know to look for. |
| `seniority.prefer` | "What level words should lift a role?" | +12. |
| `seniority.avoid` | "What level words should sink one?" | −30. Big on purpose: a mis-levelled role wastes more of a search than a mis-domained one. |
| `comp_min` | "Is there a number below which you would not take it?" | Or 0 to ignore pay entirely. See the note below. |
| `locations` | "Where, including remote?" | +3 on a match, −8 on a stated location that is not on the list. |
| `keywords_bonus` | "What domain words make a role more interesting?" | +5, once, not once per word. |
| `min_match` | Usually leave at 55. | The cutoff for what reaches the Jobs tab at all. |

**`comp_min` has a rule worth stating out loud: an unstated salary is not a failed one.** A
posting that names no pay is never penalized. Only a posting that states a band *below* the floor
is (−25). Roughly half of postings state nothing, and scoring silence as zero would quietly hide
the better half of the market.

Also set the `goals` list — the plain-language things the user is trying to accomplish this
search. This is what the dashboard's Goals tab tracks. It is for them, not for the scorer.

## Recalibration

This file is not written once. Stage 08 produces evidence about it: if six months of outcomes
show that every interview came from a `titles.medium` hit and nothing from `titles.strong` ever
replied, the strong list is aspirational and the medium list is the real search. Say so, and
offer to swap them.

Come back here whenever:

- the outcome ledger has three or more resolved applications with a visible pattern,
- the user's comp floor changes,
- the scout keeps surfacing the same wrong kind of role (the fix is almost always
  `seniority.avoid`, not `min_match`).

Next: [`03-scout.md`](03-scout.md).
