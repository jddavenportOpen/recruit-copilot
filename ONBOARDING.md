# Onboarding: your experience bank

The experience bank (`workspace/master-experience.json`) is the single source of truth for every resume this tool generates. This is the mechanical-honesty invariant: the copilot only writes what is in the bank, so **every bullet must be true and confirmable by you**. If a claim is not in the bank, it does not appear on a resume. If it is in the bank, you are standing behind it.

Start from the template:

```bash
cp workspace/master-experience.example.json workspace/master-experience.json
```

Then edit it to describe your real history. The shape is validated by [schema/experience-bank.schema.json](schema/experience-bank.schema.json).

## The four parts

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

Edit `workspace/state/target_companies.json` to control what the job scout ingests:

- **companies** the list of Greenhouse board tokens to scout (for a company careers page at `boards.greenhouse.io/acme`, the token is `acme`).
- **strong_titles** and **medium_titles** the title keywords that define a strong or medium match for your search.
- **criteria.min_match** the minimum score a role needs to show up.

Then run `/recruit:scout` (or `python3 dashboard/job_scout.py`) and open the dashboard to see your matched roles.
