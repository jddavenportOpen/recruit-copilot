---
description: Grade a resume against a specific job with the calibrated 3-persona interview panel.
---

Grade a resume against a job description using the **resume-grader** skill.

Steps:
1. Get the resume text (ask for the file/paste if not provided; extract from a PDF if needed) and
   the job description text and the employer name.
2. Score all three personas on the outcome-anchored 0-100 scale, each casting a would-interview
   vote, then assemble the panel JSON described in the `resume-grader` skill and save it to
   `"${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/panel.json`.

   **Prefer independent personas.** Dispatch the three shipped persona agents —
   `grader-hiring-manager`, `grader-recruiter`, `grader-ai-systems-rep` — **in parallel**, one
   subagent each, and collect the persona object each returns. Judges that cannot see each other
   do not anchor on each other, which is the whole point of a panel. If subagent dispatch is not
   available, fall back to scoring all three in-session per the skill; the output shape is
   identical either way.
3. Aggregate deterministically:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-grader/scripts/aggregate.py \
     "${RECRUIT_HOME:-$HOME/.recruit-copilot}"/state/panel.json
   ```
4. Report `panel_avg`, `interview_votes` out of 3, `overall_pass`, the per-persona scores, and the
   `weakest_persona` with its one-line reason, so the user knows exactly what to strengthen.

Optionally save the result next to the resume as `<name>-grade.json` in the workspace resumes dir so
the Resume tab of the dashboard shows the score.

Grade honestly. The point is to separate a genuinely strong resume from a weak one, never to inflate.
