#!/usr/bin/env python3
"""Recruit Copilot dashboard - a zero-dependency local server that reads your
recruiting workspace and serves it to the single-page app in index.html.

Run:  python3 server.py            (then open http://localhost:8765)

Your workspace lives OUTSIDE the plugin tree (see paths.py), so a plugin update
cannot strand it. Default ~/.recruit-copilot, override with $RECRUIT_HOME:
  master-experience.json     your experience bank
  resumes/                   generated resumes (+ -metadata.json, -grade.json)
  state/goals.json           your goals + search criteria
  state/jobs.json            matched roles (written by job_scout.py)

Stdlib only, so it runs anywhere Python does and ships unchanged in the plugin.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402

# The workspace lives outside the plugin tree so a plugin update cannot strand it.
HOME = paths.home(create=True)
RESUME_DIR = os.path.join(HOME, "resumes")
STATE = os.path.join(HOME, "state")
MASTER = os.path.join(HOME, "master-experience.json")
if not os.path.exists(MASTER):
    # first-run: fall back to the shipped example so the dashboard demos out of the box
    _ex = os.path.join(PLUGIN_ROOT, "workspace", "master-experience.example.json")
    if os.path.exists(_ex):
        MASTER = _ex
AGENTS_DIR = os.path.join(PLUGIN_ROOT, "agents")
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")
PORT = int(os.environ.get("RECRUIT_DASH_PORT", "8765"))


def _load_json(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def _mtime_iso(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()
    except Exception:
        return None


# ---- Tab 2: Goals (local workspace/state/goals.json) ----
def read_goals():
    d = _load_json(os.path.join(STATE, "goals.json"), None)
    if not d:
        return {"goals": [], "count": 0,
                "note": "No goals yet. Run /recruit:goals, or add them to "
                        "workspace/state/goals.json as a list of {goal, status, note}."}
    rows = d.get("goals", d) if isinstance(d, dict) else d
    out = []
    for g in rows or []:
        if isinstance(g, dict):
            out.append({"id": str(g.get("id", ""))[:8], "kind": g.get("kind", "goal"),
                        # accept either key: the goals command writes "goal", older
                        # hand-written files use "title". Silently rendering a blank row
                        # is worse than accepting both.
                        "title": g.get("title") or g.get("goal", ""),
                        "status": g.get("status", "active"),
                        "progress": g.get("progress"), "parent": g.get("parent", "")})
    return {"goals": out, "count": len(out)}


# ---- Tab 1: Resumes ----
def _derive_title(stem):
    return re.sub(r"\s+", " ", stem.replace("-", " ")).strip().title()


def read_resumes(limit=60):
    pdfs = sorted(glob.glob(os.path.join(RESUME_DIR, "*.pdf")), key=os.path.getmtime, reverse=True)
    items = []
    for pdf in pdfs[:limit]:
        stem = os.path.basename(pdf)[:-4]
        meta = _load_json(os.path.join(RESUME_DIR, f"{stem}-metadata.json"), {})
        grade = _load_json(os.path.join(RESUME_DIR, f"{stem}-grade.json"), {})
        val = meta.get("validation", {}) if isinstance(meta, dict) else {}
        items.append({
            "name": stem, "title": _derive_title(stem), "updated": _mtime_iso(pdf),
            "kb": round(os.path.getsize(pdf) / 1024, 1),
            "keyword_match_pct": meta.get("keyword_match_pct"),
            "validation_passed": val.get("passed"),
            "panel_avg": grade.get("panel_avg"), "interview_votes": grade.get("interview_votes"),
            # The average alone is not the answer. A reach employer needs 90 and a
            # majority vote; everyone else needs 70. Showing 88.9 with no verdict
            # reads as a near miss when it is a miss, which is the one thing this
            # tab exists to tell you.
            "company": grade.get("company"), "threshold": grade.get("threshold"),
            "is_reach": grade.get("is_reach"), "overall_pass": grade.get("overall_pass"),
            "weakest_persona": grade.get("weakest_persona"),
            "personas": {k: grade.get(k) for k in ("hiring_manager", "recruiter", "ai_systems_rep")} if grade.get("panel_avg") else None,
        })
    master = _load_json(MASTER, {})
    jobs = master.get("jobs", []) if isinstance(master, dict) else []
    return {"master": {"jobs": len(jobs),
                       "job_titles": [f"{j.get('title')} | {j.get('company')}" for j in jobs][:8],
                       "summaries": list((master.get("summaries") or {}).keys()),
                       "updated": _mtime_iso(MASTER)},
            "resumes": items, "count": len(items)}



# ---- Tab 3: Jobs ----
def read_jobs():
    d = _load_json(os.path.join(STATE, "jobs.json"), None)
    if d is None:
        return {"jobs": [], "search": {},
                "note": "No jobs yet. Set your goals with /recruit:goals, then run /recruit:scout "
                        "(or python3 dashboard/job_scout.py)."}
    return d



# ---- Tab 6: System health ----
def read_system():
    skills = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SKILLS_DIR, "*")) if os.path.isdir(p))
    agents = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(AGENTS_DIR, "*.md")))
    return {"total_agent_defs": len(agents), "total_skills": len(skills),
            "recruiting_specialists": agents, "recruiting_skills": skills,
            "pipeline": ["resume-intake (build the experience bank)",
                         "job_scout (ingest + score roles against your goals)",
                         "resume-builder (tailor + layout gate + round-trip gate)",
                         "resume-grader (3-persona panel, in-session)"],
            "note": "Specialists = the agents + skills this plugin ships. Claude in your session is the LLM runtime (no API key)."}




# ---- Start Here: the guided walkthrough (detects real progress from the workspace) ----
def read_setup():
    """The onboarding checklist. Each step reports whether it is DONE by inspecting the
    workspace, and the command a Claude Code user runs to do it. The dashboard turns a
    step green once its artifact exists, so a new user watches the flow complete E2E."""
    real_master = os.path.join(HOME, "master-experience.json")  # NOT the example fallback
    bank = _load_json(real_master, {})
    n_bank_jobs = len(bank.get("jobs", [])) if isinstance(bank, dict) else 0

    goals = _load_json(os.path.join(STATE, "goals.json"), {})
    goal_rows = (goals.get("goals", goals) if isinstance(goals, dict) else goals) or []
    n_goals = len(goal_rows)
    # The scout drops a starter goals.json when it refuses to run. That file is the
    # author's example, not the user's search, so it must not tick this step green.
    goals_unedited = bool(isinstance(goals, dict) and goals.get("_unedited_example"))
    has_real_search = bool(isinstance(goals, dict)
                           and ((goals.get("search") or {}).get("titles") or {}).get("strong")
                           and not goals_unedited)

    targets = _load_json(os.path.join(STATE, "target_companies.json"), {})
    n_targets = len(targets.get("companies", [])) if isinstance(targets, dict) else 0

    jobs = _load_json(os.path.join(STATE, "jobs.json"), {})
    n_jobs = len(jobs.get("jobs", [])) if isinstance(jobs, dict) else 0
    # Boards that ANSWERED, not boards you listed. A typo in a board token fails
    # silently in the tab otherwise, and "6 boards" while two 404'd is just wrong.
    _src = jobs.get("sources", []) if isinstance(jobs, dict) else []
    n_ok = sum(1 for s_ in _src if s_.get("ok"))
    n_failed = len(_src) - n_ok
    n_matched = jobs.get("total_matched", n_jobs) if isinstance(jobs, dict) else n_jobs

    pdfs = glob.glob(os.path.join(RESUME_DIR, "*.pdf"))
    graded = [g for g in glob.glob(os.path.join(RESUME_DIR, "*-grade.json"))
              if (_load_json(g, {}) or {}).get("panel_avg")]

    steps = [
        {"n": 1, "title": "Build your experience bank",
         "why": "Point it at the resumes you already have; it merges them into one honest bank every resume is drawn from.",
         "command": "/recruit:intake", "done": os.path.exists(real_master) and n_bank_jobs > 0,
         "detail": f"{n_bank_jobs} job(s) in your bank" if n_bank_jobs else "no bank yet"},
        {"n": 2, "title": "Set what you're looking for",
         "why": "Your goals and target titles decide which roles score high enough to surface.",
         "command": "/recruit:goals", "done": has_real_search,
         "detail": ("still the untouched example - edit it or run /recruit:goals" if goals_unedited
                    else (f"{n_goals} goal(s) set" if has_real_search else "no goals yet"))},
        {"n": 3, "title": "Scout roles",
         "why": "Pulls open roles from your target boards and scores each against your criteria, best first.",
         "command": "/recruit:scout", "done": n_jobs > 0,
         "detail": (f"{n_matched} role(s) matched"
                    + (f" from {n_ok} board(s)" if n_ok else (f" from {n_targets} board(s)" if n_targets else ""))
                    + (f"; {n_failed} board(s) failed, see the Jobs tab" if n_failed else "")
                    ) if n_jobs else "not scouted yet"},
        {"n": 4, "title": "Build a tailored resume",
         "why": "Selects from your bank for one posting, renders an ATS-safe PDF, and proves a machine can still read it.",
         "command": "/recruit:tailor", "done": len(pdfs) > 0,
         "detail": f"{len(pdfs)} resume(s) built" if pdfs else "none built yet"},
        {"n": 5, "title": "Grade it",
         "why": "A calibrated 3-persona panel (Hiring Manager, Recruiter, ATS) scores it honestly so you know before you send.",
         "command": "/recruit:grade", "done": len(graded) > 0,
         "detail": f"{len(graded)} resume(s) graded" if graded else "none graded yet"},
    ]
    done = sum(1 for s in steps if s["done"])
    nxt = next((s for s in steps if not s["done"]), None)
    return {"steps": steps, "done": done, "total": len(steps), "complete": done == len(steps),
            "next": nxt["n"] if nxt else None,
            "note": "Run each command in your Claude Code session. This page reflects your progress live — "
                    "refresh after each step and watch it turn green. This tool prepares your applications; it never submits."}


ROUTES = {"/api/setup": read_setup, "/api/goals": read_goals, "/api/resumes": read_resumes,
          "/api/jobs": read_jobs, "/api/system": read_system}


def _host_ok(host: str) -> bool:
    """Reject any Host header that is not literally localhost.

    Binding to 127.0.0.1 keeps other machines out, but it does NOT stop a web page
    you are browsing from pointing its own hostname at 127.0.0.1 (DNS rebinding) and
    then reading this API from your browser. Your experience bank and every resume
    would be readable by that page. Checking Host closes it.
    """
    h = (host or "").strip().lower()
    if not h:
        return False
    if h.startswith("["):                      # bracketed IPv6, e.g. [::1]:8765
        h = h.split("]")[0].lstrip("[")
    elif h.count(":") == 1:                    # host:port
        h = h.split(":")[0]
    return h in ("127.0.0.1", "localhost", "::1")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _guard(self) -> bool:
        if _host_ok(self.headers.get("Host")):
            return True
        self._send(403, json.dumps({
            "error": "refused: this dashboard only answers to localhost",
            "detail": "The Host header was not localhost. This blocks a browsed web page "
                      "from reaching your local workspace via DNS rebinding.",
        }))
        return False

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._guard():
            return
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
            except Exception as e:
                return self._send(500, f"index.html missing: {e}", "text/plain")
        if path.startswith("/resume/"):
            name = os.path.basename(path[len("/resume/"):])
            fp = os.path.join(RESUME_DIR, name)
            if name.endswith(".pdf") and os.path.isfile(fp):
                with open(fp, "rb") as fh:
                    data = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            return self._send(404, json.dumps({"error": "resume not found"}))
        if path == "/api/all":
            return self._send(200, json.dumps({k.split("/")[-1]: fn() for k, fn in ROUTES.items()}, default=str))
        if path in ROUTES:
            return self._send(200, json.dumps(ROUTES[path](), default=str))
        return self._send(404, json.dumps({"error": "not found"}))



if __name__ == "__main__":
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        print(f"Could not start the dashboard on port {PORT}: {e}\n"
              f"It may already be running at http://localhost:{PORT}. "
              f"To use another port:  RECRUIT_DASH_PORT=8790 python3 {os.path.basename(__file__)}",
              file=sys.stderr)
        sys.exit(1)
    print(f"Recruit Copilot dashboard -> http://localhost:{PORT}  (workspace: {HOME})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
