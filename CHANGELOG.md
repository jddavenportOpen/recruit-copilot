# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

Entries before 0.5.0 were reconstructed from the commit history on 2026-08-24, when this file
started being kept. From here on it is maintained with every change.

## Unreleased

Nothing yet.

## 0.5.0 — 2026-08-24

The repo becomes a **forkable methodology**. The Python is the engine; the methodology is the
product, and it is now written down where a model can execute it and a human can read it before
deciding to fork.

### Added

- **The methodology, as eight numbered stage files** under `.claude/skills/recruit-copilot/`:
  intake, goals, scout, tailor, grade, submit-tier, apply, outcome, plus a `SKILL.md` router. Each
  file is executable by a model with no other context and legible to a human deciding whether to
  fork. Because they live in `.claude/skills/`, they load automatically when the repo is opened in
  Claude Code, which is the fork path.
- **`09-invariants.md`** — the five mechanisms this repo has and others do not, with the reasoning
  behind every threshold and instructions for retuning each: the hard round-trip parse gate, the
  rendered-page layout gate, the deterministic three-persona panel arithmetic (outcome-anchored
  scale, vote-coupling, refusal to average an incomplete panel), the zero-dependency stdlib PDF
  stack, and the tiered submit policy. These existed only in code and in docstrings; a forker could
  not change a number knowingly without reading the source.
- **`/recruit:outcome`** (`commands/outcome.md`) — the loop-closer. Records what actually happened
  to an application: progress, resolution, follow-ups on a 10-day threshold with a two-follow-up
  ceiling, and a calibration handoff that says which stage a pattern belongs to. The local ledger
  is `~/.recruit-copilot/state/outcomes.json` and never leaves the machine.
- **`outcomes/`** — the anonymized public aggregate, starting at zero records. Opt-in, manual, one
  JSON file per record, reviewed as a pull request. Carries tier, role family, seniority, panel
  numbers, gate results and what happened; never the employer, the person, the URL, a date finer
  than a month, or any text from the local ledger's notes. Every threshold in this repo is a
  judgement today; this is the mechanism that can make one of them measured.
- **`CONTRIBUTING.md`** — explicit accept/reject policy, so a fork finds out what will be merged
  before building it. Includes the four-question bar for a new gate and the reproduce-on-the-real-
  path rule for claims.
- **`CHANGELOG.md`** — this file.
- **`demo/`** — a 25-second terminal recording driving the real shipped scripts (`demo.tape` for
  `vhs`, plus the two fixtures it runs against). Both gates green, then a panel at 87.8 against a
  reach threshold of 90, saying no. Nothing in it is mocked.

### Changed

- **`README.md` rewritten for a forker rather than an installer.** Leads with the demo and the
  outcome, then the five invariants as a table naming the silent failure each one catches, then the
  loop, then how to fork, with install kept as the secondary path. Adds an explicit "on results,
  honestly" section: this repo has no funnel data yet, will not borrow anyone else's, and says so.
- The opening stance is unchanged and now has its reasoning attached: it does not submit to the
  companies that matter, and that is a position, not a missing feature.

### Notes

- No Python or test changes in this release.

## 0.4.0 — 2026-08-19

### Fixed

- **The dashboard had never once loaded in a browser.** The tab dispatcher referenced a
  `renderSystem` function nobody had written: a `ReferenceError` thrown while the script was still
  evaluating, so every visitor saw "loading..." forever. It survived because every check curled
  `/api/*` and asserted on JSON, and none of them ever loaded the page. `smoke_test.py` gained two
  static guards so it cannot come back.
- **Resumes did not fill the page they took.** 9.2pt body text reads as shrunk-to-fit and still
  ended 2.3 inches short, at 76% of the usable band, with the most valuable space a candidate has
  spent on nothing. Body is now 10.4pt, `page_underfill` fires at a 12% tail instead of 30%, and it
  reports the gap **in bullets**, because "76% full" is not an instruction and "room for about 3
  more bullets" is.
- A long skills category pushed its own wrapped line three inches in; continuations now wrap back
  to a small hanging indent.
- One workspace path resolver for the whole product. The scout defaulted to the plugin's own
  `workspace/` while the dashboard defaulted to `~/.recruit-copilot`, so anyone who never set
  `RECRUIT_HOME` had the scout writing jobs into the versioned plugin directory and the Jobs tab
  reading an empty one three feet away.

## 0.3.0 — 2026-08-18

Launch hardening: data safety, real-world PDF intake, honest scoring. Six defects found by walking
the whole flow as a new user with an empty workspace.

### Fixed

- **Greenhouse ships the posting body as HTML-escaped HTML**, and the tag-stripping ran *before*
  the unescape. There are no literal angle brackets at that point, so nothing was stripped and the
  unescape then produced the markup. Every Greenhouse posting reached the tailoring and grading
  steps as a wall of `div`, `h2`, `li` and `strong`, which is what the resume's keywords were being
  matched against.
- **The Jobs tab printed the first dollar figure in a posting and the scorer compared the largest**,
  so a role shown as "$228,600" carried the sentence "posted pay clears your $300,000 floor". Both
  halves were separately defensible and the row as a whole was a lie. One parser now serves both the
  display and the decision.
- `jobs.json` dropped the posting text, so tailoring had nothing to tailor against and had to ask
  the user to paste it back in.
- `goals.json` refused to run for anyone who edited the titles by hand and left the
  `_unedited_example` marker behind, telling them their edited file was untouched. The marker now
  has to agree with the content.
- The Start Here walkthrough counted boards that were listed rather than boards that answered.
- The Resumes tab showed 88.9 with no verdict. A reach employer needs 90, so that was a miss
  reading as a near miss. Cards now carry the pass/fail against the employer's own bar.

### Added

- **Two runs may never print on top of each other** (`text_collision`), and the layout gate measures
  what will actually be drawn. This is the defect no text-based check and no round trip can see:
  overlapping glyphs extract as clean, complete text.
- **Never publish a panel score the aggregator did not produce.** Hand-averaging a real panel
  reported 88.3 where the aggregator returned 80.1: a clear pass and a clear fail from identical
  inputs.

## 0.2.0 — 2026-08-18

### Added

- **Intake** — merge the resumes you already have (PDF, DOCX, TXT, MD) into one experience bank,
  with a stdlib extractor that handles the filter chains real documents arrive with.
- **Goals-driven scouting** — scoring moved out of hardcoded keyword lists and into a `search` block
  the user owns. The scout now refuses to run against the untouched example rather than quietly
  scoring someone's career against the author's.
- **Tailoring**, and **the two machine gates**: layout QA against the rendered page, and the
  round-trip parse check against the finished PDF.

## 0.1.0 — 2026-08-17

First release. A quality-first job-search copilot for Claude Code: a resume builder and job finder
with a calibrated three-persona grading panel, and no submit path.

---

## 2026-08-24

- 14:35 — v0.5.0 docs: reshaped the repo into a forkable methodology. Added .claude/skills/recruit-copilot/ (8 numbered stage files intake->outcome + 09-invariants documenting the 5 differentiators: hard round-trip parse gate, rendered-page layout gate, deterministic 3-persona panel arithmetic, stdlib PDF stack, tiered submit policy - each with reasoning + retuning instructions). Added /recruit:outcome loop-closer + outcomes/ anonymized public aggregate. New CONTRIBUTING.md with explicit accept/reject policy, CHANGELOG.md, README rewritten for forkers, 194KB vhs demo GIF recorded from the real scripts. No Python or tests touched. smoke_test 40/40.
