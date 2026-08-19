---
name: resume-intake
description: Build the master experience bank from resumes the user already has. Reads PDF/DOCX/TXT/MD, merges every version into one deep, deduplicated bank, and validates it. Use when the user is onboarding, says they have old resumes, asks to build or update their experience bank, or has no master-experience.json yet.
---

# Resume Intake

You are building the file every future resume is drawn from. Get this right once and
every tailored resume afterwards is honest and fast. Get it wrong and you have
automated a lie.

## Why this exists

Nobody hand-writes a hundred-bullet JSON file. But almost everyone has four or five
old resumes in a folder: the long one, the one tuned for a job they did not get, the
version from two roles ago that still has the good numbers on it. That pile is the
real input.

## Procedure

**1. Find the documents.** Ask where their resumes live. Then:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-intake/scripts/extract_text.py <folder-or-files>
```

Run it without `--json` first and show the user what was found. Anything that comes
back near-empty is a scanned image; tell them to export a text PDF or paste the text.
Then re-run with `--json` to get the full text.

**2. Merge, do not summarize.** Build one bank from all of it. The bank is
deliberately far longer than any single resume, because the tailoring step needs real
choices. Rules:

- **Keep every distinct accomplishment.** The same job described three ways across
  three resumes is one job with a deeper bullet pool, not three jobs.
- **Keep the strongest phrasing of each claim, and keep variants that emphasize
  different things.** A bullet framed for a technical reader and the same work framed
  for a business reader are both worth having.
- **Never invent.** Not a number, not a title, not a date, not a scope. If two
  documents disagree, do not average them and do not pick the flattering one. Ask.
- **Flag anything that looks inflated** rather than passing it through quietly. If an
  old resume says "led a team of 40" and everything else says 12, surface it. You are
  the last reader before this becomes every future application.

**3. Ask about the gaps.** After merging, you will know what is missing: undated
roles, bullets with no outcome, a gap in the timeline. Ask a short, specific set of
questions. Do not interrogate; three good questions beat twenty.

**4. Write and validate.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-intake/scripts/validate_bank.py <path-to-bank>
```

Fix every ERROR. Walk the user through WARNs that need their judgment (overlapping
dates, a claim you could not verify). Notes are advisory.

## Schema

`schema/experience-bank.schema.json` is authoritative. The shape:

- `name` - the name that goes at the top of the resume. Required.
- `contact` - email, phone, location, links (or one `email | phone | location`
  string). Required, and the email inside it is required: a resume nobody can reply
  to fails the round-trip gate downstream.
- `jobs[]` - `id`, `title`, `company`, `location`, `dates`, `bullets` (a map of short
  id to text, kept deeper than any one resume uses), `required_bullets` (ids that must
  always appear).
- `summaries` - one per kind of role they target, keyed by archetype.
- `skills_pool` - category to comma-separated list.
- `pinned_facts` - things that must never be contradicted (legal name, work
  authorization, the title they present consistently).

## The invariant you are enforcing

Every claim in this file must be true and defensible by the user in an interview.
The tool cannot check that and neither can you. What you CAN do is refuse to write
anything they did not tell you, and surface anything that looks like it grew in the
retelling. Do both.
