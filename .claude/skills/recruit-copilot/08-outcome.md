# 08 — Outcome

**Goal of this stage:** close the loop. Record what actually happened to an application, use it
to recalibrate the stages that guessed, and, only if the user chooses, contribute an anonymized
record so the repo can eventually answer the question nobody in this category has ever answered
with data.

**Done when:** the ledger row is updated, and if the application is resolved, the user has been
told what it implies for their goals or their thresholds.

---

## Why this is the stage that matters

Every threshold in this repo is currently a **judgement**. 90 for a reach employer, 70 for
everyone else, 85 for the vote floor, 78 for a strong title hit. They are reasoned judgements, and
[`06-submit-tier.md`](06-submit-tier.md) argues each one, but nobody, in this repo or in any
competing product, can tell you what panel score actually converts to an interview, because
nobody records the other end.

That is a strange gap. There are tools that have sent millions of applications and cannot tell
you what worked, because outcomes arrive weeks later, by email, to a human, and nothing writes
them down.

One person's ledger recalibrates one person's search. A few hundred anonymized records answer
the question for everyone: **does the panel predict anything?** If a 90 converts at the same rate
as a 70, the bar is theatre and this repo should say so out loud. If it does not, that is the
first published evidence in this space that a quality gate is worth the wait.

Both outcomes are worth having. Only one of them is comfortable, which is why this has to be
mechanical rather than voluntary enthusiasm.

## Status vocabulary

Canonical spellings for the ledger's `status` field. Underscores, never spaces.

```
drafted | applied | interview | offer | hired | rejected | no_response | offer_declined | withdrawn
```

- **Final** (the application is closed): `hired`, `rejected`, `no_response`, `offer_declined`,
  `withdrawn`
- **Open**: everything else, `drafted` included
- **`drafted`** is open but distinct: nothing was sent, so no follow-up is ever due and no
  quiet-day count applies

## Procedure

**1. Load the ledger.** `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/outcomes.json`. If it does
not exist, create it as `[]`. If the user names a company, match case-insensitively; if they name
nothing, list every open row as a table (company, role, applied, status, days quiet, follow-ups
sent) and ask which to update.

List `drafted` rows under their own heading with the quiet columns blank. They are not late.

**2. Ask what happened,** and classify it:

*Progress* (still open): an interview invitation, a stage scheduled or completed, an offer
received but not yet answered.

*Resolution* (closed): `hired`, `offer_declined`, `rejected`, `no_response`, `withdrawn`.

For `no_response`, if the user is unsure whether to call it, tell them how long it has been and
let them decide. Do not impose a cutoff. An imposed cutoff turns their judgement into your
default.

Collect, without interrogating — one or two open questions is enough:

- dates for the stages reached
- any feedback received, **verbatim where they remember it**
- what they would do differently, and any signal about what the employer valued

The verbatim feedback is the highest-value text in this entire repo. It is the only unmediated
signal about what a real reader thought, and paraphrasing it into "they wanted more depth"
destroys exactly the part that was useful.

**3. Update the row.** Append to `stages` and `notes`; never rewrite history. Re-running this
stage on the same application must be idempotent: it adds, it does not duplicate.

```json
{
  "status": "interview",
  "stages": [{"stage": "phone_screen", "date": "2026-09-02", "outcome": "advanced"}],
  "notes": [{"date": "2026-09-02", "text": "Recruiter said the streaming-pricing bullet was what got the call."}]
}
```

When a row moves off `drafted`, **overwrite `applied` with the real submission date.** It was
written as the build date, and every quiet-day count downstream reads it as "sent on."

**4. Follow-ups.** An application qualifies for a follow-up when its status is neither final nor
`drafted`, **10 or more days** have passed since `applied` or since the last logged follow-up,
and it has **fewer than two** follow-ups already. Draft a short note — 60 to 120 words, in the
user's voice, addressed to the contact if there is one:

- one sentence restating interest in the specific role
- one concrete value reminder **drawn only from the submitted resume**
- one polite question about timeline

**No new claims.** A follow-up that introduces experience the submitted materials did not contain
is the fabrication invariant leaking out through a side door. The resume that was sent is the
complete set of things the note may say.

Log it as `{"date": "...", "text": "followed up"}` in `notes` in the same turn. An unlogged
follow-up breaks the next run's arithmetic.

At two follow-ups with no reply, stop. Do not offer a third. Ask whether they want to record
`no_response`.

**5. Calibrate.** Once three or more applications are resolved, or two share a pattern, say what
the data implies. Be concrete:

| Pattern | What it implies | Where it goes |
|---|---|---|
| Interviews only from `titles.medium` hits, nothing from `titles.strong` | The strong list is aspirational; the medium list is the real search | [`02-goals.md`](02-goals.md) |
| Everything under 80 went `no_response`; everything over 85 replied | `DEFAULT_THRESHOLD` of 70 is too low **for this person** | [`06-submit-tier.md`](06-submit-tier.md) |
| Reach applications that passed at 90+ still went nowhere | The bar is not the constraint. The bank is, or the warm path is | [`01-intake.md`](01-intake.md) |
| Rejections cluster in one role family | Stop applying to it, or fix what the bank says about it | [`02-goals.md`](02-goals.md) |

Recommend the change. Do not make it silently. A threshold that moves without the user noticing
is worse than one that was wrong.

## Contributing an anonymized record

**Opt-in, manual, and reviewable. Nothing here is automatic and nothing phones home.** There is
no telemetry in this repo and this stage does not add any. If the user wants to contribute, you
build the record, **show it to them in full**, and they open a pull request. Never open one on
their behalf.

Ask once per resolved application. If they say no, or say nothing, that is the end of it. Do not
re-ask on the next resolution.

### What a contributed record contains

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

### What it must never contain

The employer name. The user's name, email, phone, links, or location. The posting URL. Any date
finer than a month. Any bullet, summary or resume text. Anything from `notes` — the verbatim
feedback is the most useful text in the ledger and it is also the most identifying, so it stays
local, permanently.

`tier` replaces the employer because the tier is the only thing the aggregate needs and the name
is the only thing that identifies. `role_family` and `seniority` are coarse buckets, not titles.
`recorded` is a month, never a day.

Read the record back to the user field by field before they file anything. A record they did not
read is a record they did not consent to.

### Where it goes

One JSON file per record in `outcomes/records/`, named `<yyyy-mm>-<short-slug>.json`. One file
per record so that concurrent contributions never conflict. The aggregate table and the
contribution rules live in [`outcomes/README.md`](../../../outcomes/README.md).

Next: back to [`02-goals.md`](02-goals.md), which is where the loop closes.
