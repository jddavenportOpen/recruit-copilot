# Recruit Copilot

A quality-first job-search copilot that runs inside Claude Code. It scouts and scores target roles, tailors an ATS-safe resume, grades it with a calibrated three-persona panel, and tracks everything in a local dashboard. It fills applications up to the Submit button and stops. You click Submit.

## Why it is different

Most auto-apply tools spray a generic resume across hundreds of postings, get you flagged, and hand you a dashboard of noise. Recruit Copilot is built around two invariants that are enforced in code, not promised in marketing:

1. **It never auto-submits.** There is no submit code path. The copilot fills the form and stops so you review every application and click Submit yourself. Your account is never put at ban risk.
2. **Calibrated, honest grading.** Every resume claim traces to an experience bank you confirmed, so the tool does not invent employers, titles, or numbers. Resumes are scored by a three-persona panel on an outcome-anchored scale, not a vanity number that always reads "great."

Two more invariants: networking is drafts and tracking only (you send the messages), and reCAPTCHA is detected and handed to you, never bypassed.

## What it does

Scout, tailor, grade, track. The loop is:

```
scout target roles  ->  tailor a resume to one  ->  grade it (3-persona panel)  ->  track it in the dashboard
```

Claude in your session is the language runtime for tailoring and grading, so there is **zero marginal API cost and no API key to manage**. The shipped Python is deterministic only: it fetches postings, scores them, aggregates the panel math, and serves the dashboard.

## Install

As a Claude Code plugin, via the marketplace:

```
/plugin marketplace add jddavenportOpen/recruit-copilot
/plugin install recruit@recruit-copilot
```

Or clone it and point Claude Code at the directory:

```bash
git clone https://github.com/jddavenportOpen/recruit-copilot
cd recruit-copilot
```

Requires Python 3 (standard library only, no pip install needed) and Claude Code.

## Quickstart

1. **Onboard your experience bank.** Copy the example and fill it in with your real, confirmable history. See [ONBOARDING.md](ONBOARDING.md).

   ```bash
   cp workspace/master-experience.example.json workspace/master-experience.json
   ```

2. **Scout roles.** Edit `workspace/state/target_companies.json` to list your target boards, then:

   ```
   /recruit:scout
   ```

3. **Open the dashboard.**

   ```
   /recruit:dashboard
   ```

   Then open http://localhost:8765

4. **Grade a resume against a posting.**

   ```
   /recruit:grade
   ```

## The dashboard (6 tabs)

- **Resume** review your experience bank and every generated resume with its panel score.
- **Goals** track your search goals and progress.
- **Jobs** roles matched and scored against your criteria, best first, with comp where the posting lists it.
- **Networking** who you messaged, last contact, cadence, and meetings. Outreach stays human approved (a trust gate you turn off only when you trust it).
- **Applications** copilot runs, resume scores, and whether an application was verified as submitted. Nothing auto-submits.
- **System health** the agents and skills this plugin ships and uses.

## How grading works

Grading a resume against a job description is an LLM-as-judge problem, and naive judges fail in known ways. Recruit Copilot addresses three of them:

- **Mid-band compression.** Judges cluster everything in the 55 to 72 range. The prompt uses an outcome-anchored scale (a score band maps to a decision) so the panel actually spreads scores.
- **Score to decision decoupling.** A persona votes "would interview" while scoring the resume a 72. Vote-coupling floors a would-interview persona at 85 (`ADVANCE_FLOOR`), so a genuine yes cannot be sunk by residual compression.
- **Tiered pass.** Reach employers require a majority interview vote and a panel average of at least 90. Everyone else needs at least 70.

Claude scores three personas (hiring manager, recruiter, AI systems reviewer) across five weighted dimensions in your session. The deterministic `skills/resume-grader/scripts/aggregate.py` then does the arithmetic, so the number is never the model's own mental math. That separation is the calibration.

```bash
python3 skills/resume-grader/scripts/aggregate.py < panel.json
```

## What is v1 vs roadmap

| Capability | Status |
|---|---|
| Job scouting and scoring (public Greenhouse boards-api, ToS clean) | v1, working |
| Local 6-tab dashboard | v1, working |
| In-session calibrated 3-persona resume grading | v1, working |
| Experience-bank schema and onboarding | v1, working |
| Automated browser form-fill (fill-and-STOP) | roadmap (Greenhouse only today, being generalized) |
| Full end-to-end apply flow | roadmap |
| Hosted, multi-user SaaS version | roadmap |

## Related projects

- [mcp-judge](https://github.com/jddavenportOpen/mcp-judge) the calibrated LLM-as-judge this grading builds on, as an MCP server plus an eval harness.
- [claude-deploy-kit](https://github.com/jddavenportOpen/claude-deploy-kit) enterprise controls for deploying Claude agents safely.
- [agent-safety-case-study](https://github.com/jddavenportOpen/agent-safety-case-study) deploying a multi-agent organization safely in production.

## License

MIT. Author: JD Davenport.
