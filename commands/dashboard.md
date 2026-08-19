---
description: "Launch the local dashboard: a Start Here setup walkthrough plus Jobs, Resumes, Goals, and System Health."
---

Launch the local dashboard so the user can see their whole search in one place.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/dashboard/server.py
```

It serves on http://localhost:8765 and reads their workspace
(`${RECRUIT_HOME:-$HOME/.recruit-copilot}`). Tell the user to open that URL. The server runs
until they stop it (Ctrl-C), so start it in the background if the session needs to keep working,
and tell them the URL either way. If the port is taken it exits with a clear message; re-run with
`RECRUIT_DASH_PORT=8790` to pick another. It answers only to localhost.

The five tabs:

- **Start Here** — the guided 5-step setup walkthrough (bank → goals → scout → tailor → grade).
  Each step shows the exact command to run and turns green once its artifact exists. **Point a
  new user here first**; it is the fastest way for them to see the whole flow work end to end.
- **Jobs** — roles matched by `/recruit:scout`, best first, with the reasons behind each score.
- **Resumes** — their experience bank plus every resume built, with its panel score.
- **Goals** — the search criteria from `/recruit:goals` that everything is scored against.
- **System Health** — the agents, skills, and pipeline this plugin ships.

There is no application-tracking tab, because this tool does not apply for anyone.
