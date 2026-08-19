---
name: resume-builder
description: Tailor a resume from the experience bank to one specific job posting, render it as an ATS-safe PDF, and run the layout and round-trip gates. Use when the user wants a resume for a particular job, asks to tailor or build a resume, or picks a role from the Jobs tab.
---

# Resume Builder

One posting in, one resume out. You do the selection; Python does the typesetting and
the two machine checks.

## Procedure

**1. Read both sides.** The experience bank (`${RECRUIT_HOME:-$HOME/.recruit-copilot}/master-experience.json`) and
the job posting. If the posting is only a URL, fetch it, or ask the user to paste it.

**2. Select. Do not write.**

This is the whole discipline of this step. You are choosing from what exists, not
composing new claims.

- Take the bullets this posting actually asks for. Every `required_bullets` id for a
  job that appears must be included.
- Pick the closest summary from `summaries`. Adapt its wording to the posting's
  language; do not introduce a claim it does not already make.
- Choose skill categories the posting names. Drop the rest. A tight list beats a dump.
- Order jobs by relevance to this role, not only by date, unless that would make the
  timeline confusing.
- **You may reword for fit. You may not add facts.** Rewording means the same
  accomplishment in the posting's vocabulary. Adding facts means a number, a tool, a
  scope, or an outcome that is not in the bank. If the posting wants something the
  user does not have, leave it out and say so. A resume that quietly grows a
  qualification is the exact failure this tool exists to prevent.
- One page unless the user has more than roughly ten years of relevant history, then
  two. Never more.
- **Fill the page you take.** A one-page resume that ends two inches early is not a tight
  resume, it is a wasted one: that space is the most valuable real estate the candidate
  has and it is being spent on nothing. Select enough to reach the bottom. If the layout
  gate comes back with `page_underfill`, it tells you roughly how many more bullets fit.
  Go back to the bank, take the next most relevant ones, and rebuild. Selecting fewer
  bullets is only correct when the bank genuinely has nothing else the posting asks for,
  and then say so rather than shipping a half-empty page.

**3. Write the tailored resume JSON**, then build it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-builder/scripts/build.py \
    "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/tailored.json \
    --out "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/resumes/<company>-<role>.pdf --pages 1
```

Shape:

```json
{
  "name": "...", "contact": "email | phone | links",
  "summary": "...",
  "jobs": [{"company","title","location","dates","bullets":["..."]}],
  "education": [{"school","degree","dates","detail"}],
  "skills": {"Category": "a, b, c"},
  "additional": "optional"
}
```

**4. Read what the gates say and act on it.**

`build.py` runs two checks and they answer different questions.

- **Layout gate** measures the rendered page: page count, a contact line that wrapped,
  a bullet running five lines, an orphaned header, a margin overrun. Exit 1. These are
  content problems. Fix them by cutting words, then rebuild. Do not raise the page
  target to make a failure go away.
- **Round-trip gate** extracts the text back out of the finished PDF and diffs it.
  Exit 2. This is the one that decides whether any machine downstream can read the
  file at all. Never hand the user a resume that failed it.

Both report warnings you should relay even on a pass, especially `render_fixup`, which
tells the user what the typesetter had to change.

**5. Grade it.** Hand off to the `resume-grader` skill. Report the panel result
honestly, including a fail. A tool that says every resume is good is worth nothing.

## What this never does

It does not submit. There is no submit path in this plugin and there is not going to
be one. When the resume passes, tell the user where the PDF is and let them apply.
