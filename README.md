# Recruit Copilot

A resume builder and job finder that runs inside Claude Code. You give it the resumes
you already have, tell it what you are looking for, and it builds a tailored, ATS-safe
resume for each job you want.

**It does not apply for you.** There is no submit path in this repo and there is not
going to be one. That is the point, not a limitation.

## Why

There is a subscription industry charging $30 to $80 a month to spray applications on
your behalf. LinkedIn already takes about 11,000 job applications a minute, up 45% in
a single year, and LinkedIn attributes the surge to generative AI. Roughly half of US
job seekers were rejected at least once last year without a word from a human.

Nobody needs help sending more applications. That is the part that broke. The part
worth automating is the part that tells you the truth before you hit send.

## The loop

```
intake  ->  goals  ->  scout  ->  tailor  ->  grade  ->  you apply
```

**1. Intake.** Point it at the resumes you already have, in any mix of PDF, DOCX, TXT
and Markdown. It merges them into one experience bank that is deliberately far longer
than any resume you would send: every distinct accomplishment, several framings of the
same job, every number you can defend. That file is the only thing a resume may draw
from, so the tool cannot invent an employer, a title, or a figure.

**2. Goals.** Your target titles, level, comp floor, locations. One file, and it is
the same file the dashboard tracks, so the Jobs tab is your search rather than a feed.

**3. Scout.** Pulls open roles from public ATS boards (Greenhouse and Ashby JSON
endpoints, no auth, ToS-clean), scores each against your goals, and shows its work.
Every score comes with the reasons that produced it.

**4. Tailor.** For one posting it selects only the bullets that job asks for, picks
the closest summary, and renders a single-column PDF. Then two gates run:

- **Layout** measures the rendered page, not the text: a contact line that wrapped, a
  bullet running five lines, an orphaned section header, a URL past the margin. None
  of that exists until the document is typeset, so no text-based score can see it.
- **Round trip** pulls the text back out of the finished PDF and diffs it against what
  was laid out. If your phone number does not survive extraction, nothing downstream
  will ever see it. This is the highest-value check here and almost nobody runs it.

**5. Grade.** Three personas read the result and each casts a would-interview vote: a
recruiter doing a six-second skim, a hiring manager checking fit and believability, and
an engineer asking whether you actually built any of it. Python does the arithmetic, so
the score cannot flatter itself.

**6. You apply.** It tells you where the PDF is. You take it from there.

## Install

```
/plugin marketplace add jddavenportOpen/recruit-copilot
/plugin install recruit@recruit-copilot
```

Or clone it and point Claude Code at the directory:

```bash
git clone https://github.com/jddavenportOpen/recruit-copilot
```

Needs Python 3 and Claude Code. **Nothing to pip install** — including the PDF work,
which is why the renderer and both extractors are written against the standard
library. `pip install pymupdf` is optional and upgrades the round-trip check to an
independent, production-grade text engine.

Claude in your own session is the language runtime for intake, tailoring and grading,
so there is no API key and no marginal cost. The shipped Python is deterministic only:
it reads files, renders the PDF, measures the page, and does the panel arithmetic.

## Quickstart

```
/recruit:intake      point it at your old resumes
/recruit:goals       say what you are looking for
/recruit:scout       pull and score open roles
/recruit:tailor      build a resume for one of them
/recruit:grade       three-persona panel
/recruit:dashboard   http://localhost:8765
```

## Invariants

These are enforced in code, not promised in marketing.

1. **It never submits.** No submit path exists.
2. **It cannot invent.** Every line traces to the experience bank you confirmed.
3. **A resume a machine cannot read is never handed to you as finished.** The
   round-trip gate is a hard gate.
4. **Scoring is yours.** No target titles or comp floors are baked into the code. With
   no goals file the scout refuses to run rather than quietly scoring your career
   against somebody else's.
5. **Networking, if you use it, is drafts and tracking only.** You send the messages.

## Grading, and why it is calibrated

LLM-as-judge fails in known ways. Three are handled here:

- **Mid-band compression.** Judges cluster everything from 55 to 72. The scale is
  outcome-anchored, so a band maps to a decision and scores actually spread.
- **Score/decision decoupling.** A persona votes "would interview" and then scores a
  72. A would-interview vote floors that persona at 85.
- **Tiered pass.** Reach employers need a majority interview vote and a panel average
  of at least 90. Everyone else needs 70.

```bash
python3 skills/resume-grader/scripts/aggregate.py < panel.json
```

## Honest limits

- The round-trip check proves the text is present and recoverable in reading order from
  the finished file. It cannot prove every commercial ATS parses it correctly, because
  those are closed systems nobody can test against. It rules out the failure modes that
  are testable.
- The stdlib PDF reader handles the filter chains real resumes arrive with, and matches
  PyMuPDF's word recovery exactly across a 200-file corpus. It will still lose to a real
  engine on exotic encodings. Install PyMuPDF if you have unusual source documents.
- Scanned, image-only resumes cannot be read. There is no OCR here. Export a text PDF.
- Scouting covers Greenhouse and Ashby boards. Other ATS platforms are not wired.
- Nothing here can tell whether a claim on your resume is true. Only you can.

## Related

- [mcp-judge](https://github.com/jddavenportOpen/mcp-judge) the calibrated LLM-as-judge
  this grading builds on, as an MCP server plus an eval harness.
- [claude-deploy-kit](https://github.com/jddavenportOpen/claude-deploy-kit) enterprise
  controls for deploying Claude agents safely.
- [agent-safety-case-study](https://github.com/jddavenportOpen/agent-safety-case-study)
  deploying a multi-agent organization safely in production.

## License

MIT. Author: JD Davenport.
