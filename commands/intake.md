---
description: Build your master experience bank from the resumes you already have.
---

Build (or extend) the user's experience bank using the **resume-intake** skill.

Steps:
1. Ask where their existing resumes live. A folder is ideal; individual files are fine.
   Any of .pdf, .docx, .txt, .md.
2. Extract the text:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-intake/scripts/extract_text.py <paths>
   ```
   Show what was read. Flag anything that came back near-empty as a probable scan.
   Re-run with `--json` for the full text.
3. Follow the `resume-intake` skill to merge everything into one deep bank. Keep every
   distinct accomplishment, never invent, and surface anything that looks inflated
   rather than passing it through.
4. Ask a short set of specific questions about what is genuinely missing.
5. Write `${RECRUIT_HOME:-$CLAUDE_PLUGIN_ROOT/workspace}/master-experience.json` and validate:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/resume-intake/scripts/validate_bank.py <path>
   ```
   Fix every ERROR before finishing.

Then tell the user how deep their bank is (jobs, bullets, summaries) and that the
depth is the point: it should be far longer than any single resume, because that is
what gives tailoring real choices. Next step is `/recruit:goals`.
