# 09 — The five invariants

Reference, not a stage. This is the file to read if you are deciding whether to fork.

Everything below is a mechanism that exists in this repo and, as far as we can tell, in no
competing tool. Each one is here because it catches a failure that is otherwise **silent**: the
kind that produces no error, no bounce, and no reply, so the person running the search never
learns it happened and keeps doing it.

Each section says what the mechanism is, what it costs, where its numbers live, and how to
change them for your search. Every number here is a judgement, not a law. Change them
deliberately; [`08-outcome.md`](08-outcome.md) is how you eventually find out whether you were
right.

---

## 1. The round-trip parse gate is a hard gate

`skills/resume-builder/scripts/parse_check.py`

The PDF is rendered, then **opened again, extracted, and diffed against what was laid out.** If
the text does not come back out, the build fails and the file is never presented as finished.

**Why it exists.** Everything else in this category grades the *text you gave it*. But nothing
downstream ever sees that text. They see a PDF, run through a parser you cannot inspect. Between
those two things sits a class of failure that produces no error anywhere: a phone number
swallowed by a header region, a whole employer lost to column interleaving, an export that came
out as an image, glyphs that render correctly and extract as nothing. The resume looks perfect on
screen. It arrives empty. Nobody tells you, because from the employer's side nothing went wrong.
You just didn't have the keywords.

The only way to know is to read the finished file back. It is a cheap check and almost nobody
runs it.

**Where the numbers are.** Recovery-rate floor **0.6**, absolute floor **120 characters**,
`MIN_CHARS` **400** for the no-source-text case.

The rate matters more than the length, and that distinction was a bug fix: a new grad with one
short job has a perfectly extractable 260-character resume, and a fixed length floor fails them
with "this is probably a scanned image," which is both wrong and unactionable. Compare against
what was actually laid out.

**Hard breakers** (nothing may proceed): recovery under 60%, and **no email survived**. The email
is singled out because a resume nobody can reply to is a silent reject and is invisible to every
other check here.

**Retuning.** Raise 0.6 toward 0.8 if your renderer is reliable and you want a stricter signal;
below 0.5 the gate stops meaning anything. Do not remove the email breaker.

**The honest limit.** Passing proves the text is present and recoverable in reading order from
the finished file. It does not prove every commercial ATS parses it correctly — those are closed
systems nobody can test against. It rules out the failure modes that are testable, which is more
than a resume normally gets. Do not let anyone describe this as "ATS-verified."

---

## 2. The layout gate measures the rendered page, not the text

`skills/resume-builder/scripts/format_qa.py`

The renderer emits a `.layout.json` next to the PDF holding every line's text and its bounding
box in PDF points. The gate reads *that*: real glyph positions, not a character-count estimate.

**Why it exists.** A second class of defect **does not exist until the document is typeset**. In
the source text, the contact line has not wrapped yet, the bullet has not run to five lines, the
section header is not yet stranded at the foot of a page, the long employer name is not yet
printing on top of its own date range. A text-based score cannot see any of it, because none of
it has happened.

**The one with no substitute is `text_collision`.** Two runs overlapping on the same baseline
still extract as clean, complete, correctly-ordered text. The round-trip gate passes it. Every
parser passes it. Only a human opening the PDF sees the defect, and the first human to open it is
the one deciding.

**Where the numbers are.**

| Constant | Ships as | What it governs |
|---|---|---|
| `OVERFLOW_SLACK` / `OVERFLOW_HARD` | 1.5pt / 6.0pt | Warning vs error on a right-margin overrun |
| `COLLISION_SLACK` | 0.5pt | Two runs on a baseline may touch, never overlap |
| `MAX_BULLET_LINES` | 2 | 3 if the bullet contains a URL |
| `MIN_BULLET_WORDS` | 4 | Below this it is a fragment, not a bullet |
| `UNDERFILL` | 0.12 | A one-pager stopping 12% early is unused real estate |
| `TOP_MARGIN` / `BOT_MARGIN` | 52.0 / 46.0 | The band `UNDERFILL` is measured against |

**Retuning.** `MAX_BULLET_LINES` is the one most worth changing: 2 is right for a one-page
engineering resume and wrong for an academic CV, where 3 or 4 is normal. `UNDERFILL` is a
warning, never an error, on purpose, because a genuinely short career should produce a short resume, and
the gate's job is to make sure that was a choice.

**The rule that makes the gate worth having:** fix the content, never the threshold. If you find
yourself raising `--pages` to clear `page_overflow`, you have converted a real defect into a
configuration value.

---

## 3. The panel arithmetic is deterministic, and decoupled from the votes

`skills/resume-grader/scripts/aggregate.py`

The model scores three personas across five weighted dimensions and casts three
would-interview votes. **A Python script does every calculation from there.** The model never
computes, estimates, or reports a panel number.

**Why it exists.** LLM-as-judge fails in known, documented ways, and three of them are handled
here rather than hoped away.

**a. Mid-band compression.** Judges cluster everything into roughly 55–72, so every resume comes
back "pretty good" and the score carries no decision. The fix is not a stern instruction, it is
an **outcome-anchored scale** where each band maps to an action: 90–100 strong yes, 85–89 would
interview, 70–84 borderline, 55–69 likely no, 40–54 weak, 0–39 reject. A band is a decision, so
the scale has to spread.

**b. Score/vote decoupling.** The verdict and the number come from different parts of the
reasoning and drift apart. A persona says "yes, I'd interview them" and scores a 72. `ADVANCE_FLOOR`
**floors any would-interview persona at 85**, so a genuine yes cannot be sunk by residual
compression. This is a correction, not a thumb on the scale: it only ever fires when the persona
has already committed to advancing the candidate.

**c. The arithmetic is not the model's.** This is not a stylistic preference. Measured on a real
resume, hand-averaging the same panel reported **88.3** where the aggregator returned **80.1** — a
clear pass and a clear fail from identical inputs. A mental average silently skips both the
weighting and the tiered bar, and it reads high, always in the flattering direction.

**d. An incomplete panel is a failed run, not a low score.** If a persona is missing, or any one
of its five dimensions is unscored, the script exits 3 and refuses to produce a number. Averaging
around a gap would report one persona at 90 with two absent as **30/100**, a confident, wrong
verdict. This distinction is load-bearing and it is the first thing to preserve in a fork.

**Where the numbers are.** Weights: impact 25, relevance 25, keywords 20, employer-convention 15,
structure 15. `ADVANCE_FLOOR` 85. The composite always divides by the **full** rubric weight, never
by whatever dimensions happened to be present. Renormalizing would let a persona scored on one
dimension report that single score as its composite.

**Retuning.** The weights are the honest lever: impact and relevance carry half the total because
they are the two a human reader cannot be talked out of, but a research role plausibly weights
`experience_domain_relevance` at 35 and `target_employer_convention_fit` at 5. Keep the five
weights summing to 100.

---

## 4. The PDF stack is the standard library, on purpose

`skills/resume-builder/scripts/pdfwrite.py` (writer) · `pdftext.py` (reader) ·
`render_resume.py` (typesetter)

About 850 lines, no dependencies. `pip install` is not part of getting started.

**Why it exists.** This is not minimalism for its own sake. It falls out of the thesis. The
whole product claim is that a resume has to survive being read by a machine, and the maximally
parseable artifact is a specific thing: **single column, base-14 fonts only, no embedded font
programs, no CID mapping, no images, uncompressed content stream.** That is not what a general
PDF library optimizes for; it is what this writer emits, always, and it needs nothing but the
standard library to do it.

The writer also **returns the layout it produced**, which is what makes invariant 2 possible at
all. A library that hands back only bytes cannot tell you where a line landed.

The reader has to handle a harder problem: the resumes people already have, produced by Word,
Pages, LaTeX, reportlab or a browser print. So it decodes real filter chains (**ASCII85 then
Flate** is what reportlab emits, and a decoder that only knows Flate returns nothing on those,
which looks exactly like a scanned image and sends the user down entirely the wrong path), and it
parses **`/ToUnicode` CMaps** (`bfchar` and `bfrange`) so Type0 and Identity-H CID fonts (what
Google Docs, Word and browser "print to PDF" emit) come back as text rather than glyph ids.

**The honest limit.** It is a few hundred lines, not a PDF engine. Word spacing on heavily kerned
files is reconstructed from glyph positions and is not always perfect, and an Identity CID font
with no `ToUnicode` map cannot be recovered at all. `pip install pymupdf` is optional and upgrades
both intake and the round-trip gate to a real, independent text engine — **and the gate reports
which engine ran**, so you can see for yourself whether the two agree on your own files. Scanned,
image-only resumes cannot be read by either. There is no OCR here.

**Retuning.** If you fork this and swap in a real PDF library, keep two properties or invariant 2
dies with the change: the writer must return per-line bounding boxes, and the round-trip
extractor must be a **different** engine from the writer. A round trip through the same library's
own reader mostly proves that library is self-consistent.

---

## 5. The submit tier, and never-auto on the companies that matter

`skills/resume-grader/scripts/aggregate.py` · full reasoning in
[`06-submit-tier.md`](06-submit-tier.md)

Applications are not interchangeable units of volume. A standard employer is repeatable; a reach
employer is close to one-shot, and the cost of a weak application there is not the rejection, it
is that you spent your one read at the company you actually wanted while your resume was two
revisions from ready.

So the bar is set by the cost of being wrong:

| Tier | Bar |
|---|---|
| Reach | **2 of 3 interview votes AND `panel_avg >= 90`** |
| Standard | `panel_avg >= 70` |

The reach bar is a **conjunction** and that is the important part. A high average alone can be
carried by one enthusiastic judge; two votes alone can wave through a resume that is thin
everywhere. Requiring both means the application has to be good *and* convince more than one kind
of reader.

**And there is no submit path in this repo: not for reach employers, not for standard ones, not
behind a flag.** That is a position, not a missing feature. Automated submission is only
attractive at volume; volume is only cheap at standard employers; and the moment a tool can
submit at standard employers, the reach list is a config value standing between a user and their
own worst instinct at 1am. Every spray-and-pray product in this category began as a careful one
with a threshold.

There is a simpler reason too. Invariant 1 proves a machine can read the page. Invariant 3 proves
three judges would advance it. **Neither can prove a claim on it is true.** Only the person whose
name is at the top can do that, and asking them costs fifteen seconds.

**Where the numbers are.** `REACH_THRESHOLD` 90, `DEFAULT_THRESHOLD` 70, and the `REACH` set,
18 companies as shipped, matched on a normalized name.

**Retuning.** The `REACH` set is the first thing to change in a fork, and it is not a claim about
which companies are good. A specific 40-person startup you have wanted to work at for three years
is a reach employer *for you*; a famous company you would take only if nothing else worked is
not, whatever its logo is worth. `DEFAULT_THRESHOLD` is the most defensible thing to tune from
your own ledger. `REACH_THRESHOLD` should not move without outcome data, because 90 is the top
band on the scale and a reach bar below "strong yes" is not a bar.

If you add submission to a fork, inherit the policy rather than inventing one. The five
conditions are in [`06-submit-tier.md`](06-submit-tier.md).

---

## What is deliberately not here

Stated so nobody mistakes an absence for an oversight:

- **No cover letters.** They are a real gap, not a position. See `CONTRIBUTING.md`.
- **No interview prep.** Same.
- **No telemetry.** Nothing in this repo phones home, including
  [`08-outcome.md`](08-outcome.md), whose contribution path is a pull request the user reads
  before they file it.
- **No submit path.** See invariant 5.
- **No OCR.** See invariant 4.
- **No claim-verification.** Nothing here can tell whether something on a resume is true. Only
  the person sending it can, and every stage says so.
