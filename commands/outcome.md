---
description: Record what actually happened to an application - an interview, an offer, a rejection, silence - and recalibrate the search from it.
---

Close the loop on an application. The full stage spec, including the status vocabulary, the
follow-up rules and the anonymized-contribution contract, is
`.claude/skills/recruit-copilot/08-outcome.md`. Follow it; this command is the entry point, not a
second copy of the rules.

`$ARGUMENTS` may be:
- nothing — list every open application and ask which to update
- a company name, optionally with a role (`/recruit:outcome acme`, `/recruit:outcome acme staff engineer`)
- `followup` — draft follow-ups for every application that has gone quiet (10-day default)
- `followup <N>` or `followup <company>` — a different threshold, or one specific application now

Steps:

1. **Load the ledger.** `"${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/outcomes.json`, or create
   it as `[]`. With no argument, list the open rows as a table (company, role, applied, status,
   days quiet, follow-ups sent) and ask which one. List `drafted` rows under their own heading
   with the quiet columns blank; nothing was sent, so nobody is late replying. If the application
   was made outside this tool, collect company, role, date applied and posting URL and add a row.

2. **Ask what happened**, then classify it as a progress update (interview invitation, stage
   completed, offer received) or a resolution (`hired`, `offer_declined`, `rejected`,
   `no_response`, `withdrawn`). Collect the dates of stages reached, any feedback **verbatim where
   they remember it**, and what they would do differently. Do not interrogate. Two open questions
   is enough. For `no_response`, tell them how long it has been and let them decide; never impose
   a cutoff.

3. **Update the row.** Append to `stages` and `notes` with dates; never rewrite history. Re-running
   this on the same application must add, not duplicate. When a row moves off `drafted`, overwrite
   `applied` with the real submission date. It was written as the build date, and every quiet-day
   count downstream reads it as "sent on".

4. **Follow-up branch** (`followup`, or offer it when a row is 10+ days quiet with fewer than two
   follow-ups logged). Draft 60 to 120 words in the user's voice: interest in the specific role,
   one concrete reminder **drawn only from the resume that was actually sent**, one polite question
   about timeline. No new claims. The submitted resume is the complete set of things the note may
   say. Log it to `notes` in the same turn. At two follow-ups with no reply, stop and ask about
   recording `no_response`.

5. **Calibrate.** Once three applications are resolved, or two share a pattern, say what it implies
   and where it goes: `02-goals.md` for the search, `06-submit-tier.md` for the thresholds,
   `01-intake.md` when the bank is the constraint. Recommend the change; never make it silently.

6. **Offer to contribute an anonymized record**, once, and only on a resolved application. Build
   the record per `08-outcome.md`, **read it back field by field**, and let the user open the pull
   request themselves. Never open one on their behalf. If they decline, do not ask again.

The record carries tier, role family, seniority, panel numbers, gate results and what happened. It
never carries the employer, their name or contact details, the posting URL, any date finer than a
month, or any text from `notes`. Nothing here is automatic and nothing phones home.
