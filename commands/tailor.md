---
description: Build a resume for one specific job, then run the layout and round-trip gates.
---

Tailor a resume for a single posting using the **resume-builder** skill.

Steps:
1. Get the posting. A URL from the Jobs tab, a pasted description, or a company and
   title to look up. Get the employer name; the grader's pass bar depends on it.
2. Load the experience bank. If there is no `master-experience.json`, stop and run
   `/recruit:intake` first; there is nothing to build from.
3. Follow the `resume-builder` skill to SELECT from the bank. Reword for fit, never
   add a fact. If the posting wants something the user does not have, leave it out and
   tell them.
4. Build it:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-builder/scripts/build.py \
       /tmp/tailored.json --out <workspace>/resumes/<company>-<role>.pdf --pages 1
   ```
5. Act on the gates. Layout failure (exit 1) means cut words and rebuild; never raise
   the page target to silence it. Round-trip failure (exit 2) means a machine cannot
   read the file, so it does not get sent. Relay warnings even on a pass.
6. Grade it with `/recruit:grade` and report the panel honestly, including a fail.

Finish by telling the user where the PDF is. Do not offer to submit it; this tool
has no submit path by design.
