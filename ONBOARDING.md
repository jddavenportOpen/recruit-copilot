# Onboarding: your experience bank

The experience bank is the single source of truth for every resume this tool generates. This is the mechanical-honesty invariant: the copilot only writes what is in the bank, so **every bullet must be true and confirmable by you**. If a claim is not in the bank, it does not appear on a resume. If it is in the bank, you are standing behind it.

**The easy way: run `/recruit:intake`.** Point it at the resumes you already have, in any mix of PDF, DOCX, TXT and Markdown, and it merges them into the bank for you, asking about anything that looks inflated or contradictory. Most people should do this instead of hand-writing JSON.

The rest of this document is for understanding the file, or filling it in by hand.

## Where it lives

Your bank is `master-experience.json` inside your workspace, which is `~/.recruit-copilot` by default (override with `$RECRUIT_HOME`). That is deliberately outside the plugin directory so a plugin update cannot touch it. To start from the shipped template by hand:

```bash
mkdir -p ~/.recruit-copilot
cp "$CLAUDE_PLUGIN_ROOT"/workspace/master-experience.example.json ~/.recruit-copilot/master-experience.json
```

Then edit it to describe your real history, and check it with:

```bash
python3 "$CLAUDE_PLUGIN_ROOT"/skills/resume-intake/scripts/validate_bank.py ~/.recruit-copilot/master-experience.json
```

The shape is validated by [schema/experience-bank.schema.json](schema/experience-bank.schema.json).

## The parts

Before the four content sections below, the file needs two identity fields: **`name`** and **`contact`** (an object with `email`, `phone`, `location`, and optional `links`). The email matters more than it looks — the round-trip gate checks that your contact details survive extraction from the finished PDF, because a resume nobody can reply to is worse than no resume. An `education` array is optional but usually worth having.

### 1. jobs

An array of your roles, most recent first. Each job has an `id`, `title`, `company`, `location`, `dates`, a `bullets` object, and a `required_bullets` list.

- **bullets** is a map from a short bullet id to the bullet text. Keep a deep pool here, more than any one resume will use, so the tailoring step can pick the bullets that match a given posting. Write each bullet as a concrete, quantified accomplishment you can defend in an interview.
- **required_bullets** is the list of bullet ids that must always appear for this job, no matter the posting. Use it for your strongest, most load-bearing accomplishments.

### 2. summaries

A map from an archetype name to a summary paragraph. Different postings call for a different framing of the same career, so write one summary per archetype you target (for example `applied-ai`, `solutions`, `product`). The tailoring step picks the closest match.

### 3. skills_pool

A map from a category name to a comma-separated list of skills. Keep these focused and real. A recruiter skims this in seconds, so a tight, credible list beats a keyword dump.

### 4. pinned_facts (optional)

A list of short statements that must never be contradicted, for example your legal name, work authorization, or a title you present consistently. Treat these as guardrails on generation.

## A worked example

One job entry looks like this:

```json
{
  "id": "acme-2023",
  "title": "Staff Engineer",
  "company": "Acme Robotics",
  "location": "Remote",
  "dates": "2023 to Present",
  "bullets": {
    "throughput": "Cut order-processing latency from 4s to 380ms by moving the pricing path to a streaming pipeline, lifting checkout conversion 6 percent.",
    "team": "Led a team of 5 engineers and set the review and on-call practices the platform group later adopted.",
    "cost": "Reduced cloud spend 22 percent by right-sizing the batch fleet and adding autoscaling on real demand signals."
  },
  "required_bullets": ["throughput"]
}
```

Here `throughput` always appears (it is the strongest line); `team` and `cost` are pulled in when the posting calls for leadership or cost work.

## Setting your targets for the scout

Two different files, and it is worth knowing which does what.

**What gets scouted — `state/target_companies.json`.** This controls only *which boards*
are read. Each row is `{"name": ..., "ats": "greenhouse" | "ashby", "token": ...}`, where
the token is the board slug: for `boards.greenhouse.io/acme` it is `acme`; for an Ashby
board at `jobs.ashbyhq.com/acme` it is `acme`. `ats` defaults to `greenhouse` if you leave
it out. If the file does not exist, a small built-in list of AI companies is used, so you
can try the scout before deciding on targets.

```json
{"companies": [
  {"name": "Acme",  "ats": "greenhouse", "token": "acme"},
  {"name": "Globex", "ats": "ashby",     "token": "globex"}
]}
```

**How roles are scored — `state/goals.json`.** Every title keyword, seniority preference,
comp floor, location, and the `min_match` cutoff lives here, in the `search` block. This
is the file that decides what counts as a match. Run `/recruit:goals` to fill it in by
answering a few questions, or edit it directly. The scout refuses to run until it exists,
rather than quietly scoring your career against somebody else's defaults.

Then run `/recruit:scout` and open the dashboard's Jobs tab to see your matched roles,
each with the reasons that produced its score.
