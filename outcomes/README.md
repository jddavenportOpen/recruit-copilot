# Outcomes

**The question:** does a panel score predict anything?

Every threshold in this repo is a reasoned judgement. 90 for a reach employer, 70 for everyone
else, 85 for the vote floor. They are argued in
[`.claude/skills/recruit-copilot/09-invariants.md`](../.claude/skills/recruit-copilot/09-invariants.md),
and not one of them is measured, because nobody in this category records the other end of the
funnel. Tools have sent millions of applications and cannot tell you what worked, because outcomes arrive
weeks later, by email, to a human, and nothing writes them down.

This directory is the attempt to fix that in the open. Enough anonymized records and the answer is
knowable: **if an 88 converts at the same rate as a 68, the bar is theatre and this repo should say
so.** If it does not, that is the first published evidence in this space that a quality gate is
worth the wait.

Both answers are worth having. Only one of them is comfortable.

## The aggregate

| | |
|---|---|
| Records contributed | **0** |
| Applications represented | **0** |
| Last updated | 2026-08-24 |

Not enough data to say anything. That line stays exactly as it is until there is.

When there is, this table gets the breakdown that matters, reply rate and interview rate by
`panel_avg` band split by tier, and every claim in the README about what a score means will be
either backed by it or removed.

## Contributing a record

Opt-in, manual, and reviewable. **Nothing in this repo phones home.** There is no telemetry, no
account, and no background upload. A record reaches this directory exactly one way: you read it,
you open a pull request, a human reviews it.

1. Run `/recruit:outcome` on a **resolved** application. It builds the record and reads it back to
   you field by field. A record you did not read is a record you did not consent to.
2. Save it as `outcomes/records/<yyyy-mm>-<short-slug>.json`. One file per record, so concurrent
   contributions never conflict.
3. Open a PR titled `outcome: <role family>, <tier>`. No other changes in the same PR.

### The record

```json
{
  "schema": 1,
  "recorded": "2026-09",
  "tier": "reach",
  "role_family": "backend engineering",
  "seniority": "senior",
  "panel_avg": 87.8,
  "interview_votes": 2,
  "threshold": 90,
  "overall_pass": false,
  "weakest_persona": "ai_systems_rep",
  "gates": {"layout": "pass", "round_trip": "pass", "engine": "stdlib"},
  "sent": true,
  "result": "interview",
  "stages_reached": 2,
  "days_to_first_reply": 9
}
```

| Field | Values |
|---|---|
| `schema` | `1` |
| `recorded` | `YYYY-MM`. **Month only, never a day.** |
| `tier` | `reach` \| `standard` |
| `role_family` | A coarse bucket, not a job title: `backend engineering`, `product management`, `data science`, `applied ai`, `consulting` |
| `seniority` | `entry` \| `mid` \| `senior` \| `staff` \| `principal` \| `director` |
| `panel_avg`, `interview_votes`, `threshold`, `overall_pass`, `weakest_persona` | Exactly as `aggregate.py` printed them |
| `gates` | `layout` and `round_trip` each `pass` \| `fail`, plus the extraction `engine` |
| `sent` | Whether it was actually submitted. A record where `sent` is false and `overall_pass` is false is **useful data**, not a non-event |
| `result` | `interview` \| `offer` \| `hired` \| `rejected` \| `no_response` \| `offer_declined` \| `withdrawn` |
| `stages_reached` | Integer. 0 if it never advanced |
| `days_to_first_reply` | Integer, or `null` if there was never a reply |

### What a record must never contain

The employer name. Your name, email, phone, links, or location. The posting URL. Any date finer
than a month. Any bullet, summary, or resume text. Anything from the `notes` field of your local
ledger. The verbatim feedback is the most useful text in your ledger and it is also the most
identifying, so it stays on your machine, permanently.

`tier` replaces the employer because the tier is the only thing the aggregate needs and the name
is the only thing that identifies.

**A PR carrying any of the above will be closed with an explanation, not merged and then
scrubbed** — a rewritten commit is still in the fork network, and the person it identifies cannot
undo that. This is the one review rule here with no discretion in it.

## Your own ledger stays yours

The full record (employer, URL, resume path, verbatim feedback, everything) lives in
`~/.recruit-copilot/state/outcomes.json`, outside the repo, gitignored at the source, never
uploaded. What you contribute here is a derived subset you looked at first.
