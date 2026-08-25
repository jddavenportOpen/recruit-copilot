# 01 — Intake

**Goal of this stage:** produce one file, the experience bank, that every future resume is
drawn from and that nothing downstream is allowed to add to.

**Done when:** `${RECRUIT_HOME:-$HOME/.recruit-copilot}/master-experience.json` exists and
`validate_bank.py` reports no errors.

---

## Why the bank exists

Two problems, one file.

The first is honesty. A model asked to "write a resume for this job" will produce a good resume
for that job, and some of it will not be true, not maliciously, but because fluency fills gaps.
The fix is structural, not a prompt: give the writing step a closed set of facts and forbid it
from leaving that set. The bank is that set. Stage 04 may reword anything in it and may add
nothing to it, which means the only place a false claim can enter this system is here, in front
of the person who would have to defend it in an interview.

The second is that tailoring needs choices. A resume tailored from a resume is just a resume
with the adjectives changed. Tailoring from a bank that holds three framings of the same job and
twice as many bullets as any one page can hold is a genuine selection problem, and selection is
where the fit actually comes from.

So the bank is deliberately far longer than any resume anyone would send.

## Why you are not asking them to write it

Nobody hand-writes a hundred-bullet JSON file, and the ones who try write a worse bank than the
one already sitting in their Documents folder. Almost everyone has four or five old resumes: the
long one, the one tuned for a job they did not get, the version from two roles ago that still
has the good numbers on it. That pile is the real input. Read it.

## Procedure

**1. Find the documents.**

Ask where their resumes live. A folder is ideal; individual files are fine. Any mix of `.pdf`,
`.docx`, `.txt`, `.md`, `.json`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/skills/resume-intake/scripts/extract_text.py <folder-or-files>
```

Run it without `--json` first and show the user what came back. **Anything that comes back
near-empty is a scanned image, not an empty resume** — say so and ask them to export a text PDF
or paste the text. There is no OCR here and pretending otherwise wastes their afternoon.

Then re-run with `--json` for the full text.

**2. Merge. Do not summarize.**

- **Keep every distinct accomplishment.** The same job described three ways across three resumes
  is one job with a deeper bullet pool, not three jobs.
- **Keep the strongest phrasing, and keep variants that emphasize different things.** A bullet
  framed for a technical reader and the same work framed for a business reader are both worth
  having; stage 04 will pick between them.
- **Never invent.** Not a number, not a title, not a date, not a scope.
- **When two documents disagree, do not average and do not pick the flattering one. Ask.**
- **Flag anything that looks like it grew in the retelling.** If one resume says "led a team of
  40" and everything else says 12, surface it. You are the last reader before this becomes every
  future application.

**3. Ask about the gaps.** After merging you will know what is missing: an undated role, a bullet
with no outcome, a hole in the timeline. Ask a short, specific set of questions. Three good ones
beat twenty; this is the step where people abandon the tool.

**4. Write and validate.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/skills/resume-intake/scripts/validate_bank.py \
    "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/master-experience.json
```

Fix every ERROR. Walk the user through the WARNs that need their judgement (overlapping dates, a
claim you could not corroborate). Notes are advisory.

## The shape

`schema/experience-bank.schema.json` is authoritative. In brief:

| Field | Holds |
|---|---|
| `name` | The name that goes at the top. Required. |
| `contact` | Email, phone, location, links. Required, and the **email is load-bearing** — stage 04's round-trip gate hard-fails a PDF whose email does not survive extraction. |
| `jobs[]` | `id`, `title`, `company`, `location`, `dates`, `bullets` (a map of short id to text, kept deeper than any one resume uses), `required_bullets` (ids that must always appear). |
| `summaries` | One per archetype of role they target, keyed by archetype. Stage 04 picks the closest. |
| `skills_pool` | Category to comma-separated list. |
| `pinned_facts` | Statements that must never be contradicted: legal name, work authorization, the title they present consistently. |

## The invariant you are enforcing

Every claim in this file must be true and defensible by the user in an interview. No tool can
check that and neither can you. What you **can** do is refuse to write anything they did not tell
you, and surface anything that reads like it grew. Do both, every time.

Next: [`02-goals.md`](02-goals.md).
