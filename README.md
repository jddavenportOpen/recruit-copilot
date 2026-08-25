# Recruit Copilot

*A job search is a verification problem. This is the methodology, and the engine under it.*

<p align="center">
  <img src="demo/recruit-copilot.gif" alt="Building a resume: both machine gates pass, then the three-persona panel returns 87.8 against a threshold of 90 and says no." width="820">
</p>

**It does not submit to the companies that matter. That is the point, not a limitation.**

To be precise about the state today: there is **no submit path in this repo at all**, for any
employer, behind any flag. The reasoning is a tier system, not squeamishness — a standard employer
is a repeatable event, a reach employer is close to one-shot, and the moment a tool can submit at
the cheap end, the expensive end is a config value standing between you and your worst instinct at
1am. Full argument: [`06-submit-tier.md`](.claude/skills/recruit-copilot/06-submit-tier.md).

## What you get

Point it at the resumes you already have. It merges them into one experience bank, scores open
roles against goals **you** wrote, and for a posting you pick it builds a tailored single-column
PDF. Then it does the part nobody else does:

- It **measures the rendered page**: the contact line that wrapped, the bullet running five
  lines, the employer name printing on top of its own date range.
- It **opens the finished PDF and reads the text back out**, and hard-fails if your email did not
  survive.
- It runs **three independent judges** (a recruiter's six-second skim, a hiring manager, and the
  ATS itself), and a Python script does the arithmetic, so the score cannot flatter itself.
- It applies **the bar that matches what this employer costs to get wrong**, and tells you no when
  you have not cleared it.

Then it stops, tells you where the file is, and you apply.

### On results, honestly

This repo has no funnel data yet, and it will not borrow anyone else's. Every threshold in here
(90 for a reach employer, 70 for everyone else, 85 for the vote floor) is a **reasoned judgement**,
argued in the open, and not one of them is measured.

That is the gap [`/recruit:outcome`](.claude/skills/recruit-copilot/08-outcome.md) exists to close.
Record what happened to an application, and if you want to, contribute an anonymized record: tier,
role family, panel score, what happened. No employer, no name, no URL, no date finer than a month,
nothing that phones home.

Enough of those and the question becomes answerable: **does a panel score predict anything?** If an
88 converts at the same rate as a 68, the bar is theatre and this repo will say so. Nobody in this
category can answer that today, because nobody records the other end.
[`outcomes/README.md`](outcomes/README.md) is where it accumulates, in public, starting at zero.

## Why it is built this way

There is a subscription industry charging $30 to $80 a month to spray applications on your behalf.
LinkedIn already takes about 11,000 job applications a minute, up 45% in a single year, and
attributes the surge to generative AI. Roughly half of US job seekers were rejected at least once
last year without a word from a human.

Nobody needs help sending more applications. That is the part that broke. The part worth automating
is the part that tells you the truth before you hit send.

## The five invariants

Enforced in code, not promised here. Each one catches a failure that is otherwise **silent**: no
error, no bounce, no reply, so you never learn it happened and you keep doing it. Every threshold
below is a judgement you can change, and
[`09-invariants.md`](.claude/skills/recruit-copilot/09-invariants.md) gives the reasoning for each
so you can change it knowingly.

| # | Invariant | The silent failure it catches |
|---|---|---|
| 1 | **The round-trip gate is hard.** The PDF is opened, extracted, and diffed against what was laid out | A phone number swallowed by a header region, a whole employer lost to column interleaving, an export that came out as an image. Looks perfect on screen, arrives empty |
| 2 | **The layout gate measures the rendered page**, from real glyph bounding boxes | Overlapping text, which extracts as clean, complete, correctly-ordered text. No parser can see it. Only the hiring manager can |
| 3 | **The panel arithmetic is deterministic**, with an outcome-anchored scale and vote-coupling | LLM judges cluster at 55–72 and vote yes while scoring 72. Hand-averaging one real panel read **88.3** where the aggregator returned **80.1** |
| 4 | **The PDF stack is standard library**, ~850 lines, writer and reader | reportlab's ASCII85-then-Flate returns nothing to a Flate-only decoder, which looks exactly like a scanned image and sends you down the wrong path |
| 5 | **The submit tier, and never-auto on the companies that matter** | Spending your one read at the company you actually wanted while your resume was two revisions from ready |

Two more that are not mechanisms but are absolute: **it cannot invent**, because every line traces to a
bank entry you confirmed, and **your data stays on your machine**. The only network calls are to
public job boards.

## The loop

```
   01 intake ──▶ 02 goals ──▶ 03 scout ──▶ 04 tailor ──▶ 05 grade
                    ▲                                        │
                    │                                        ▼
                08 outcome ◀── 07 apply ◀────────── 06 submit-tier
```

Eight files under [`.claude/skills/recruit-copilot/`](.claude/skills/recruit-copilot/), one per
stage. Each is executable by a model with no other context and readable by a human deciding
whether to fork.

| | Stage | Decides |
|---|---|---|
| [01](.claude/skills/recruit-copilot/01-intake.md) | Intake | What is true about you, in one bank every resume draws from |
| [02](.claude/skills/recruit-copilot/02-goals.md) | Goals | What counts as a job worth your attention |
| [03](.claude/skills/recruit-copilot/03-scout.md) | Scout | Which open roles clear that bar, and why |
| [04](.claude/skills/recruit-copilot/04-tailor.md) | Tailor | What goes on the page, and whether a machine can read the page |
| [05](.claude/skills/recruit-copilot/05-grade.md) | Grade | Whether three independent judges would advance it |
| [06](.claude/skills/recruit-copilot/06-submit-tier.md) | Submit tier | What this employer costs to get wrong, and what bar that sets |
| [07](.claude/skills/recruit-copilot/07-apply.md) | Apply | The handoff to you, and the ledger row |
| [08](.claude/skills/recruit-copilot/08-outcome.md) | Outcome | What actually happened, and what that should change |

Plus [09-invariants.md](.claude/skills/recruit-copilot/09-invariants.md), the reference: the five
mechanisms, every threshold, and how to retune each one.

## Fork it

The methodology is the product. It is written to be taken, and four things in it are yours, not the
author's:

```bash
gh repo fork jddavenportOpen/recruit-copilot --clone
cd recruit-copilot
claude
```

The skill loads automatically when you open Claude Code in the repo. Then change:

| What | Where | Why it is yours |
|---|---|---|
| The reach employers | `REACH` in `skills/resume-grader/scripts/aggregate.py` | A 40-person startup you have wanted for three years is a reach employer *for you*. A famous company you would take only if nothing else worked is not, whatever its logo is worth |
| The two pass bars | `REACH_THRESHOLD` / `DEFAULT_THRESHOLD`, same file | 90 and 70 are judgements. Yours should come from your ledger |
| The boards | `~/.recruit-copilot/state/target_companies.json` | Coverage here is by company, not by keyword |
| The search | `~/.recruit-copilot/state/goals.json` | The scout **refuses to run** without it rather than score your career against a stranger's defaults |

> **Your experience bank never leaves your machine.** It lives in `~/.recruit-copilot`, outside the
> repo, and the workspace paths are gitignored at the source. A fork of a public repo is public;
> nothing in this repo will put your career history in it, but check before you push anyway.

If your fork learns something — a gate that caught what ours missed, an ATS adapter, a threshold
your outcomes justified — send it back. [`CONTRIBUTING.md`](CONTRIBUTING.md) says exactly what gets
merged and what gets declined, so you find out before you build it, not after.

## Or install it

From your terminal. This block is safe to paste whole:

```bash
claude plugin marketplace add jddavenportOpen/recruit-copilot && claude plugin install recruit@recruit-copilot
```

Or from inside Claude Code, one command at a time. Paste both lines together and
`/plugin marketplace add` reads the second line as part of the repo name, then fails with
"not a valid GitHub owner/repo shorthand".

```
/plugin marketplace add jddavenportOpen/recruit-copilot
```

```
/plugin install recruit@recruit-copilot
```

Then restart Claude Code (or run `/reload-plugins`) and type `/recruit:` to see the commands.

```
/recruit:intake      point it at your old resumes
/recruit:goals       say what you are looking for
/recruit:scout       pull and score open roles
/recruit:tailor      build a resume for one of them
/recruit:grade       three-persona panel
/recruit:outcome     record what happened
/recruit:dashboard   http://localhost:8765
```

New here? Run `/recruit:dashboard` first and open the **Start Here** tab. It walks the setup in
order, shows the exact command to run next, and turns each step green as you finish it.

Needs Python 3.9+ and Claude Code. **Nothing to pip install**, including the PDF work. See
invariant 4. `pip install pymupdf` is optional and upgrades the round-trip check to an independent,
production-grade text engine. Claude in your own session is the language runtime for intake,
tailoring and grading, so there is no API key and no marginal cost.

Everything you create lives in `~/.recruit-copilot` (override with `$RECRUIT_HOME`), deliberately
outside the plugin directory, so updating never touches your bank or your resumes.

Want to hand-write the experience bank? See [ONBOARDING.md](ONBOARDING.md).

## Honest limits

- The round-trip check proves the text is present and recoverable in reading order from the
  finished file. It **cannot** prove every commercial ATS parses it correctly — those are closed
  systems nobody can test against. It rules out the failure modes that are testable. Do not let
  anyone describe this as "ATS-verified."
- The stdlib PDF reader handles what real resumes arrive as: the common filter chains, and the
  CID/Type0 fonts with `ToUnicode` maps that Google Docs, Word and browser "print to PDF" emit. It
  is still a few hundred lines, not a PDF engine. Word spacing on heavily kerned files is
  reconstructed from glyph positions and is not always perfect. `pip install pymupdf` and both
  intake and the gate switch to it automatically; **the gate reports which engine it used**, so you
  can see whether the two agree on your own files.
- Scanned, image-only resumes cannot be read. There is no OCR here.
- Scouting covers Greenhouse and Ashby. Lever, Workday and the rest are not wired. That is the largest
  open gap in the repo, and a welcome contribution.
- No cover letters and no interview prep yet. Gaps, not positions.
- **Nothing here can tell whether a claim on your resume is true.** Only you can. Every stage says
  so, in those words.

## Checking your install

```bash
python3 smoke_test.py
```

Builds a throwaway workspace in a temp directory, drives the real shipped scripts the way the
`/recruit:` commands do, and checks what comes out: every script runs on stdlib alone, the example
bank validates, a real PDF is produced with both gates green, the panel arithmetic matches the
documented rules, and the dashboard serves every tab. No network, no API key, and it never touches
your own workspace. Run it after cloning, and before opening a pull request.

The demo above is not a mockup — it is [`demo/demo.tape`](demo/demo.tape) driving the real shipped
scripts against the fixtures in that folder. Re-record it with `vhs demo/demo.tape`.

## Related

- [mcp-judge](https://github.com/jddavenportOpen/mcp-judge) is the calibrated LLM-as-judge this
  grading builds on, as an MCP server plus an eval harness.
- [claude-deploy-kit](https://github.com/jddavenportOpen/claude-deploy-kit) is enterprise controls
  for deploying Claude agents safely.
- [agent-safety-case-study](https://github.com/jddavenportOpen/agent-safety-case-study) is deploying
  a multi-agent organization safely in production.

## License

MIT. Author: JD Davenport. Changes are recorded in [CHANGELOG.md](CHANGELOG.md).
