# 04 — Tailor

**Goal of this stage:** one posting in, one resume out, with proof that a machine can still read
what came out.

**Done when:** `build.py` exits 0. Any other exit code means you are not done, and the numbers in
this file tell you which kind of not-done you are in.

---

## The discipline: select, do not write

You are choosing from the bank, not composing. Rewording is allowed; adding is not.

- **Rewording** means the same accomplishment in the posting's vocabulary.
- **Adding** means a number, a tool, a scope, or an outcome that is not in the bank.

If the posting asks for something the user does not have, **leave it out and tell them**. A
resume that quietly grows a qualification is the exact failure this repo exists to prevent, and
it is the one failure mode nothing downstream can catch: a fabricated bullet renders perfectly,
extracts perfectly, and scores well.

Rules of selection:

- Every `required_bullets` id for a job that appears must be included.
- Pick the closest `summaries` entry and adapt its wording. Do not introduce a claim it does not
  already make.
- Choose the skill categories the posting names; drop the rest. A tight list beats a dump.
- Order jobs by relevance to this role, not only by date, unless that makes the timeline
  confusing.
- One page unless the user has more than roughly ten years of relevant history, then two.
  Never more.
- **Fill the page you take.** A one-pager that ends two inches early is not a tight resume, it is
  a wasted one: that space is the most valuable real estate the candidate has and it is being
  spent on nothing. The layout gate measures this and tells you roughly how many more bullets
  fit. Go back to the bank and take the next most relevant ones.

## Build

Write the tailored resume JSON, then build it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/skills/resume-builder/scripts/build.py \
    "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/tailored.json \
    --out "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/resumes/<company>-<role>.pdf --pages 1
```

Shape:

```json
{
  "name": "...", "contact": "email | phone | location | links",
  "summary": "...",
  "jobs": [{"company": "", "title": "", "location": "", "dates": "", "bullets": ["..."]}],
  "education": [{"school": "", "degree": "", "dates": "", "detail": ""}],
  "skills": {"Category": "a, b, c"},
  "additional": "optional"
}
```

`build.py` runs `render → layout gate → round-trip gate` in that order and returns:

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Both gates passed | Go to stage 05 |
| 1 | Layout gate failed | Cut words, rebuild. **Never raise `--pages` to make it pass.** |
| 2 | Round-trip failed | Do not hand this file over. See below. |
| 3 | Bad input | The JSON is malformed. This is not a layout problem; do not go cut bullets. |

## Gate one: layout, measured on the rendered page

`format_qa.py` reads the `.layout.json` the renderer writes next to the PDF — every line's text
and its bounding box in PDF points, so every check is against real glyph positions rather than a
character-count guess.

It exists because a class of defect **does not exist until the document is typeset**: the contact
line that wrapped to two rows, the bullet that runs five lines, the section header stranded alone
at the foot of a page, the URL that overruns the right margin, the long employer name printing on
top of its own date range. No text-based score can see any of it, because in the source text none
of it has happened yet.

Errors (exit 1):

| Code | Trips when |
|---|---|
| `page_overflow` | More pages than the target |
| `contact_wrap` | The contact line takes more than one row |
| `margin_overflow` | More than 6.0pt past the right text edge (1.5–6.0pt is a warning) |
| `text_collision` | Two runs on one baseline overlap by more than 0.5pt |
| `long_bullet` | A bullet runs 2 or more lines past its cap (cap is 2 lines, 3 if it contains a URL) |
| `banned_glyph` | An em dash, en dash, curly apostrophe or bullet glyph survived to the page |
| `empty_document` | Nothing rendered |

Warnings worth relaying: `page_underfill` (the page stops early, with an estimate of how many
more bullets fit), `split_bullet`, `orphan_header`, `thin_bullet`, `runt_page`, and especially
`render_fixup`, which tells the user what the typesetter silently changed to keep the file
parseable.

**`text_collision` is the check with no substitute.** Overlapping glyphs still extract as clean,
complete, correctly-ordered text. The round-trip gate cannot see the defect. A parser cannot see
it. Only a person opening the PDF sees it, and by then it is the hiring manager.

## Gate two: round-trip, extracted back out of the finished file

`parse_check.py` opens the PDF that was just written, pulls the text back out, and diffs it
against what was laid out. This is the check almost nobody runs and it is the one that decides
whether any machine downstream ever sees the resume at all.

Two extractors, strongest first: **PyMuPDF** if the user happens to have it (a real, independent,
production-grade text engine, so agreement with it is real evidence), otherwise the shipped stdlib
content-stream reader. The result names which engine ran, so the user can judge the strength of
the evidence themselves.

Hard failures (`hard_breaker`, nothing downstream should proceed):

- **Recovery rate below 60%** of the characters that were laid out. Note that the check is a
  *rate*, not a length. A new grad with one short job can have a perfectly extractable
  260-character resume, and failing them with "this is probably an image" is wrong and
  unactionable advice. The absolute floor of 120 characters exists only for the genuinely empty
  case.
- **No email survived.** A resume nobody can reply to is a silent reject, and it is invisible to
  every other check in this repo.

Soft failures (the gate still fails, and the file still should not be sent):

- No phone number survived.
- A standard section header (`experience`, `education`, `skills`) missing from the extracted text.
- An employer name that did not survive — a whole role may be unreadable.
- Any word of four or more letters present in the source that did not come back out. This catches
  silent glyph loss, which is otherwise undetectable.

**The honest limit, stated because overclaiming is the thing this repo is against:** passing
proves the text is present and recoverable in reading order from the finished file. It does not
prove that every commercial ATS parses it correctly, because those are closed systems nobody can
test against. It rules out the failure modes that are testable, which is more than a resume
normally gets.

## When a gate fails

Fix the content. Do not fix the gate. If you find yourself raising `--pages`, widening a
threshold, or reaching for a different renderer to make a red light go green, stop. The gate is
reporting a real defect in a document about to be read by a stranger who owes the user nothing.

Next: [`05-grade.md`](05-grade.md).
