# Contributing

This repo has a narrow philosophy and it is written down, so most declined work is well-executed
work that did not know the policy. Ten minutes here will save you an afternoon.

## The one rule everything follows from

**This repo optimizes for the application not sent.**

Every other tool in this category optimizes throughput. This one exists because throughput is the
part that broke: LinkedIn takes roughly 11,000 applications a minute, up 45% in a single year,
and about half of US job seekers were rejected at least once last year without hearing from a
human. Nobody needs help sending more. The scarce thing is a tool that tells you the truth before
you hit send.

The corollary: **a contribution is judged on fit to that rule first and execution second.** Good
code pointed the other way still gets declined, kindly and with reasons.

The second rule, downstream of the first: **the model decides, the script counts.** Judgement
calls belong in markdown a model reads. Arithmetic belongs in deterministic Python. A change that
moves a number from the script into the model is moving in the wrong direction even when the
number comes out the same.

## What gets merged

- **A new gate that catches a silent failure**, with the failing case demonstrated. Silent is the
  operative word: a defect that produces an error somewhere is already handled by something. The
  gates here exist because a resume can lose its phone number, or print two runs on top of each
  other, and nothing anywhere reports it.
- **More determinism.** Moving a calculation out of the model and into a script, or turning a
  soft warning into a check with a number behind it.
- **ATS coverage.** Adapters for Lever, Workday, SmartRecruiters and the rest, against **public,
  unauthenticated endpoints only**, matching the shape of `fetch_greenhouse` / `fetch_ashby` in
  `dashboard/job_scout.py`. This is the largest open gap in the repo.
- **Extraction robustness.** A real PDF that `pdftext.py` reads as empty or garbled is a genuine
  bug report; attach the file, or a minimal one that reproduces it.
- **Outcome records.** See [`outcomes/README.md`](outcomes/README.md). These are the highest-value
  contribution anyone can make and they take four minutes.
- **Documented honest limits.** If something here overclaims, saying so precisely is a merge.
- **Cover letters and interview prep.** Both are real gaps, not positions. Same rules apply: the
  cover letter may only draw on the experience bank, and it needs a gate of its own or a stated
  reason it does not.

## What gets declined

- **A submit path.** Any code that fills, posts, or automates an application form, at any tier,
  behind any flag. This is invariant 5 and it is not a backlog item. The reasoning is in
  [`.claude/skills/recruit-copilot/06-submit-tier.md`](.claude/skills/recruit-copilot/06-submit-tier.md).
  Build it in your fork; the five conditions to inherit if you do are in that same file.
- **Telemetry, analytics, or any background network call.** The only network calls in this repo
  are to public job boards, and the outcome path is a pull request a human reads first. A PR that
  adds a phone-home is declined on sight regardless of what it collects.
- **Runtime dependencies in the core path.** Rendering, extraction, layout QA and the aggregator
  are standard library and stay that way. PyMuPDF is the model for how a dependency is allowed to
  exist here: **optional, detected at runtime, and the code names which engine it used.**
- **Personal data.** A populated experience bank, a real resume, a real posting URL with someone's
  application in it. The shipped example bank is fictional and stays that way.
- **Threshold changes without evidence.** "90 is too strict" is not an argument; three resolved
  outcomes showing 85s converted is. Tuning a number so a specific resume passes is moving the
  goalposts with the score on the board.
- **Scoring defaults that are somebody else's.** The scout refuses to run without a goals file on
  purpose. A PR that adds a "sensible default" search block reintroduces the exact failure that
  refusal exists to prevent.
- **Anything against a job board's terms**, anything requiring auth to a site that did not offer
  it, and anything that needs a CAPTCHA solved.
- **A second copy of the workflow.** The markdown under `.claude/skills/recruit-copilot/` **is**
  the implementation. A parallel command tree for another agent runtime drifts from it the moment
  either changes, and cannot be verified here. Fork it: the numbered files are portable, and a
  thin pointer that references them ages far better than a copy.
- **Kitchen-sink PRs.** One concern per PR. Bundles get asked to split, and splits get reviewed
  fast.

## The bar for a new gate

The gates are the product, so the bar is high and it is specific. A new gate has to answer all
four:

1. **What silent failure does it catch?** Name it. If a person or an existing check already
   notices, it is a lint, not a gate.
2. **Can it be measured, or is it a judgement?** Gates are deterministic. Judgements go in the
   methodology markdown, where a model applies them and a human can argue with them.
3. **Does it fail the build, or warn?** Say which and defend it. `page_underfill` is a warning
   because a genuinely short career should produce a short resume. "No email survived" is a hard
   breaker because the application is already dead and nothing else here can see it.
4. **What is its false-positive story?** The recovery-rate floor started as a character count and
   failed new grads with short, perfectly extractable resumes. A gate that cries wolf gets
   disabled, and a disabled gate catches nothing.

## Claims get verified

Reviews here are empirical, and the same standard applies to a bug report and to a fix.

- **State the failing case and how to reproduce it.** A description of a problem is not a problem.
- **Reproduce on the real path, not a constructed input.** A test that fails before and passes
  after is necessary and not sufficient, because the failing input has to be one the workflow actually
  produces. Show it through `build.py`, through `job_scout.py`, through a real PDF. A fix whose
  only demonstration is a synthetic value fed straight to a function gets declined even with a
  green test.
- **Run the smoke test before you open the PR:**
  ```bash
  python3 smoke_test.py
  ```
  It builds a throwaway workspace in a temp dir, drives the real shipped scripts the way the
  `/recruit:` commands do, and checks what comes out: every script runs on stdlib alone, the
  example bank validates, a real PDF is produced with both gates green, the panel arithmetic
  matches the documented rules, and the dashboard serves every tab. No network, no API key, and it
  never touches your own workspace.
- **There is no CI yet.** Wiring the smoke test into GitHub Actions is a welcome contribution and
  the kind of infrastructure that is argued from a problem that exists.

**There are no precedents to cite yet.** This repo is young enough that the first PRs will set
them, and when they do this file will name them the way a maintained policy should.

## Forking for your own search

Most people should fork rather than contribute, and that is a success, not a consolation. The
methodology is written to be taken.

1. Fork it, then change the four things that are yours:
   - the `REACH` set in `skills/resume-grader/scripts/aggregate.py` — your reach employers, not
     the author's
   - `REACH_THRESHOLD` and `DEFAULT_THRESHOLD`, once your ledger has an opinion
   - `state/target_companies.json` — the boards you actually care about
   - `state/goals.json` — the search itself
2. The reasoning behind every one of those numbers is in
   [`.claude/skills/recruit-copilot/09-invariants.md`](.claude/skills/recruit-copilot/09-invariants.md),
   so you can change them knowingly rather than by feel.
3. **Your experience bank never leaves your machine.** It lives in `~/.recruit-copilot`, outside
   the repo, and the workspace paths are gitignored at the source. Check before you push anyway.
4. If your fork learns something (a gate that caught something ours missed, an ATS adapter, a
   threshold your outcomes justified), send it back. That is the whole point of the shape.

One practical warning: when you open a PR from a fork, GitHub targets the upstream repo by
default, not yours. Check the base repository dropdown before you publish, especially on a commit
that touches your workspace.

## Credit

A change that incorporates your code gets a `Co-authored-by` trailer. A change written
independently from your report or diagnosis gets a named mention in the commit and the PR. Both
happen without being asked for.
