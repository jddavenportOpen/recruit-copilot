---
description: Launch the local recruiting dashboard (Resume, Goals, Jobs, Networking, Applications, System health).
---

Launch the local dashboard so the user can see their whole search in one place.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/dashboard/server.py
```

It serves on http://localhost:8765 and reads the local workspace
(`${RECRUIT_HOME:-$CLAUDE_PLUGIN_ROOT/workspace}`). Tell the user to open that URL. The server runs
until they stop it (Ctrl-C), so start it in the background if the session needs to keep working, and
tell them the URL either way.

The six tabs: Resume (their bank + generated resumes with panel scores), Goals, Jobs (matched roles
from `/recruit:scout`), Networking (contacts + a trust gate that keeps outreach human-approved),
Applications (runs, scores, and verified-applied), and System health (the agents and skills this
plugin ships).
