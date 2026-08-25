# 07 — Apply

**Goal of this stage:** hand the finished artifact to the person whose name is on it, with
everything they need to send it in the next five minutes, and open the ledger row that stage 08
will close.

**Done when:** the user has the file path, knows the tier verdict, and there is a `sent` (or
`drafted`) row in the outcome ledger.

---

## The handoff

The tool stops here. Say four things, in this order:

1. **Where the file is.** The full path. Not "your resume is ready."
2. **What the panel said.** `weakest_persona` and its reason first, then `panel_avg` against the
   threshold, then the vote count. If it did not clear the bar, lead with that.
3. **What the gates found that they should know about even on a pass.** `render_fixup` (what the
   typesetter silently changed), `page_underfill` (unused page), and which extraction engine ran
   — `stdlib` is the fallback, and telling them `pip install pymupdf` upgrades the round-trip
   check to an independent engine is a thirty-second improvement to their evidence.
4. **What is still theirs to check.** Every claim on the page is true and defensible. No tool in
   this repo can verify that, and the person about to send it is the only one who can.

Then stop. Do not open a browser, do not fill a form, do not offer to. See
[`06-submit-tier.md`](06-submit-tier.md) for why that is a position and not a gap.

## When it did not clear the bar

Do not soften it and do not offer to send it anyway.

The useful move is specific: `weakest_persona` names the seat that would have rejected it, and
its `reason` names what was missing. Take that back to stage 04 and rebuild. Most reach-tier
misses come back at 90+ after one revision, because the gap is usually a genuinely absent
keyword or a bullet that was in the bank and did not get selected, both of which are fixable in
one pass without inventing anything.

If two revisions do not close it, the honest read is usually that the bank does not contain what
this posting is asking for. Say that. It is more useful than a third revision, and it is
information about the search, which belongs back in [`02-goals.md`](02-goals.md).

## Open the ledger row now

The single most common way a job search loses its own data is: apply, mean to write it down,
never write it down. Open the row at the moment of the handoff, while every field is known and
nobody has to remember anything.

Append to `${RECRUIT_HOME:-$HOME/.recruit-copilot}/state/outcomes.json` (create it as `[]` if it
does not exist):

```json
{
  "id": "examplecorp-staff-engineer-2026-08",
  "company": "Example Corp",
  "role": "Staff Engineer",
  "url": "https://boards.greenhouse.io/examplecorp/jobs/1234567",
  "tier": "standard",
  "applied": "2026-08-24",
  "status": "drafted",
  "resume": "/Users/you/.recruit-copilot/resumes/examplecorp-staff-engineer.pdf",
  "panel": {"panel_avg": 84.2, "interview_votes": 2, "threshold": 70, "overall_pass": true,
            "weakest_persona": "ai_systems_rep"},
  "gates": {"layout": "pass", "round_trip": "pass", "engine": "stdlib"},
  "stages": [],
  "notes": []
}
```

Two rules that keep this file honest:

- **`status` starts at `drafted` and only becomes `applied` when the user says they sent it.** A
  drafted row is not a pending application — nobody is late replying to something that was never
  sent, and counting drafts as applications is how a search convinces itself it is busier than it
  is.
- **`applied` is the date it was actually sent**, not the date the PDF was built. Stage 08 counts
  quiet days from it.

The file is in the workspace, which is outside the repo and gitignored at the source. It never
leaves the machine.

Next: [`08-outcome.md`](08-outcome.md), the stage everybody skips, and the only one
that makes the rest of this measurable.
