#!/usr/bin/env python3
"""Recruit Copilot dashboard - a zero-dependency local server that reads your
recruiting workspace and serves it to the single-page app in index.html.

Run:  python3 server.py            (then open http://localhost:8765)

All state lives under a local workspace dir (RECRUIT_HOME, default ../workspace):
  workspace/master-experience.json     your experience bank
  workspace/resumes/                    generated resumes (+ -metadata.json, -grade.json)
  workspace/state/goals.json            your goals
  workspace/state/jobs.json             matched roles (written by job_scout.py)
  workspace/state/apply_ledger.json     application runs
  workspace/state/contacts.json         networking log

Stdlib only, so it runs anywhere Python does and ships unchanged in the plugin.
"""
import glob
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
HOME = os.environ.get("RECRUIT_HOME", os.path.join(PLUGIN_ROOT, "workspace"))
RESUME_DIR = os.path.join(HOME, "resumes")
STATE = os.path.join(HOME, "state")
MASTER = os.path.join(HOME, "master-experience.json")
if not os.path.exists(MASTER):
    # first-run: fall back to the shipped example so the dashboard demos out of the box
    _ex = os.path.join(HOME, "master-experience.example.json")
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
            "personas": {k: grade.get(k) for k in ("hiring_manager", "recruiter", "ai_systems_rep")} if grade.get("panel_avg") else None,
        })
    master = _load_json(MASTER, {})
    jobs = master.get("jobs", []) if isinstance(master, dict) else []
    return {"master": {"jobs": len(jobs),
                       "job_titles": [f"{j.get('title')} | {j.get('company')}" for j in jobs][:8],
                       "summaries": list((master.get("summaries") or {}).keys()),
                       "updated": _mtime_iso(MASTER)},
            "resumes": items, "count": len(items)}


# ---- Tab 5: Applications ----
def read_applications():
    d = _load_json(os.path.join(STATE, "apply_ledger.json"), {})
    batches = d.get("batches", [])
    recent, scores = [], []
    for b in batches[-30:]:
        for r in (b.get("results") or []):
            sc = r.get("scores") or {}
            if isinstance(sc.get("panel_avg"), (int, float)):
                scores.append(sc["panel_avg"])
            recent.append({"ts": b.get("ts"), "company": r.get("company", ""), "title": r.get("title", ""),
                           "status": r.get("status", ""), "panel_avg": sc.get("panel_avg"),
                           "verified_applied": r.get("verified_applied", False)})
    return {"total_batches": len(batches), "officially_submitted": len(d.get("applied_urls", [])),
            "verified_applied": sum(1 for r in recent if r.get("verified_applied")),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
            "recent": list(reversed(recent))[:40],
            "note": "The copilot fills and STOPS; you click Submit. 'Verified applied' means a confirmation was detected."}


# ---- Tab 3: Jobs ----
def read_jobs():
    d = _load_json(os.path.join(STATE, "jobs.json"), None)
    if d is None:
        return {"jobs": [], "search": {},
                "note": "No jobs yet. Set your goals with /recruit:goals, then run /recruit:scout "
                        "(or python3 dashboard/job_scout.py)."}
    return d


# ---- Tab 4: Networking ----
def read_networking():
    d = _load_json(os.path.join(STATE, "contacts.json"), None)
    if d is None:
        return {"contacts": [], "meetings": [],
                "trust_gate": {"outreach_automation": "OFF",
                               "reason": "Outreach stays human-approved until your messaging is proven not-AI-sounding and not ban-risk."},
                "note": "No contacts yet. Track who you messaged, last-contact date, cadence, and meetings in workspace/state/contacts.json."}
    d.setdefault("trust_gate", {"outreach_automation": "OFF"})
    return d


# ---- Tab 6: System health ----
def read_system():
    skills = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SKILLS_DIR, "*")) if os.path.isdir(p))
    agents = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(AGENTS_DIR, "*.md")))
    return {"total_agent_defs": len(agents), "total_skills": len(skills),
            "recruiting_specialists": agents, "recruiting_skills": skills,
            "pipeline": ["job_scout (ingest+score)", "resume-generator skill (tailor)",
                         "resume-grader skill (3-persona panel, in-session)", "format gate (ATS parse-safety)",
                         "resume-intake (build the experience bank)", "resume-builder (tailor + layout + round-trip gates)"],
            "note": "Specialists = the agents + skills this plugin ships. Claude in your session is the LLM runtime (no API key)."}


# ---- Review flow (companies x jobs, each with its resume + score + approve) ----
def read_review():
    d = _load_json(os.path.join(STATE, "review.json"), None)
    if d is None:
        return {"companies": [], "generated": None,
                "note": "No review batch yet. Scout roles, then generate + grade a resume per role, then approve."}
    order = d.get("companies_order") or []
    by_co = {}
    for r in d.get("results", []):
        by_co.setdefault(r["company"], []).append(r)
    companies = []
    for name in order or list(by_co.keys()):
        jobs = by_co.get(name, [])
        ready = [j for j in jobs if (j.get("panel_avg") or 0) > 0]
        companies.append({"name": name, "jobs": jobs, "ready": len(ready), "total": len(jobs),
                          "approved": sum(1 for j in jobs if j.get("approved")),
                          "avg": round(sum(j["panel_avg"] for j in ready) / len(ready), 1) if ready else None})
    results = d.get("results", [])
    return {"companies": companies, "generated": d.get("generated"),
            "totals": {"jobs": len(results), "scored": sum(1 for r in results if (r.get("panel_avg") or 0) > 0),
                       "approved": sum(1 for r in results if r.get("approved"))},
            "note": "The copilot fills applications and STOPS at Submit. Approving marks a resume ready; you click Submit."}


def _mutate_review(fn):
    p = os.path.join(STATE, "review.json")
    d = _load_json(p, None)
    if not d:
        return {"ok": False}
    n = fn(d.get("results", []))
    with open(p, "w") as fh:
        json.dump(d, fh, indent=2, default=str)
    return {"ok": True, "updated": n}


ROUTES = {"/api/goals": read_goals, "/api/resumes": read_resumes, "/api/applications": read_applications,
          "/api/jobs": read_jobs, "/api/networking": read_networking, "/api/system": read_system,
          "/api/review": read_review}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
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

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or "{}") if length else {}
        except Exception:
            body = {}
        if path == "/api/approve":
            pdf, appr = body.get("pdf"), body.get("approved", True)
            return self._send(200, json.dumps(_mutate_review(
                lambda rows: sum(1 for r in rows if r.get("pdf") == pdf and (r.update(approved=bool(appr)) or True)))))
        if path == "/api/approve-all":
            appr = body.get("approved", True)
            return self._send(200, json.dumps(_mutate_review(
                lambda rows: sum(1 for r in rows if (r.get("panel_avg") or 0) > 0 and (r.update(approved=bool(appr)) or True)))))
        return self._send(404, json.dumps({"error": "not found"}))


if __name__ == "__main__":
    print(f"Recruit Copilot dashboard -> http://localhost:{PORT}  (workspace: {HOME})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
