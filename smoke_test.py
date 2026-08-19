#!/usr/bin/env python3
"""Smoke test: prove a fresh clone actually works, end to end, with no network and
no API key. Run it after cloning, or before opening a PR.

    python3 smoke_test.py

It builds a throwaway workspace in a temp dir, drives the real shipped scripts the
same way the /recruit: commands do, and checks the artifacts that result. It never
touches your own workspace and never talks to the network.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"  [{PASS if ok else FAIL}] {name}{('  - ' + detail) if detail else ''}")
    return ok


def run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run([PY] + args, capture_output=True, text=True, timeout=120, **kw)


def main() -> int:
    print("recruit-copilot smoke test\n")
    ws = tempfile.mkdtemp(prefix="recruit-smoke-")
    os.makedirs(os.path.join(ws, "resumes"), exist_ok=True)
    os.makedirs(os.path.join(ws, "state"), exist_ok=True)
    try:
        # 1. Every shipped script imports and responds to --help (stdlib only).
        print("1. shipped scripts run (stdlib only)")
        scripts = [
            "skills/resume-builder/scripts/build.py",
            "skills/resume-builder/scripts/format_qa.py",
            "skills/resume-builder/scripts/parse_check.py",
            "skills/resume-grader/scripts/aggregate.py",
            "skills/resume-intake/scripts/validate_bank.py",
            "skills/resume-intake/scripts/extract_text.py",
            "dashboard/job_scout.py",
            "dashboard/search_goals.py",
        ]
        for s in scripts:
            p = run([os.path.join(ROOT, s), "--help"])
            check(f"{s} --help", p.returncode == 0, (p.stderr or "").strip().splitlines()[-1] if p.returncode else "")

        # 2. The shipped example bank validates against the schema.
        print("\n2. example experience bank is valid")
        bank_src = os.path.join(ROOT, "workspace", "master-experience.example.json")
        p = run([os.path.join(ROOT, "skills/resume-intake/scripts/validate_bank.py"), bank_src])
        check("example bank validates", p.returncode == 0, (p.stdout or p.stderr)[-160:].strip())

        # 3. Tailor + build: the example bank -> a real PDF, both machine gates green.
        print("\n3. build a resume (render + layout gate + round-trip gate)")
        bank = json.load(open(bank_src))
        c = bank["contact"]
        job = bank["jobs"][0]
        tailored = {
            "name": bank["name"],
            "contact": " | ".join([c["email"], c["phone"], c["location"], *c.get("links", [])]),
            "summary": list(bank["summaries"].values())[0],
            "jobs": [{"title": j["title"], "company": j["company"], "location": j["location"],
                      "dates": j["dates"], "bullets": list(j["bullets"].values())[:3]}
                     for j in bank["jobs"]],
            "education": bank.get("education", []),
            "skills": bank["skills_pool"],
            "additional": "",
        }
        tpath = os.path.join(ws, "tailored.json")
        json.dump(tailored, open(tpath, "w"))
        pdf = os.path.join(ws, "resumes", "smoke-test.pdf")
        p = run([os.path.join(ROOT, "skills/resume-builder/scripts/build.py"), tpath, "--out", pdf, "--pages", "1"])
        check("build.py exits 0 (both gates passed)", p.returncode == 0,
              f"exit={p.returncode} {(p.stdout or p.stderr)[-200:].strip()}")
        check("PDF exists and is non-trivial", os.path.exists(pdf) and os.path.getsize(pdf) > 1000,
              f"{os.path.getsize(pdf) if os.path.exists(pdf) else 0} bytes")
        if os.path.exists(pdf):
            with open(pdf, "rb") as fh:
                check("PDF has a valid header", fh.read(5) == b"%PDF-", "")

        # 4. Grading math: a known panel must produce the documented numbers.
        print("\n4. panel aggregation math")
        def persona(score, vote):
            keys = ["quantified_impact_credibility", "keyword_requirement_coverage",
                    "experience_domain_relevance", "target_employer_convention_fit",
                    "structure_clarity_execution"]
            return {"dimensions": {k: {"score": score} for k in keys},
                    "would_interview": vote, "reason": "smoke"}
        panel = {"company": "Example Co",
                 "personas": {"hiring_manager": persona(80, True),
                              "recruiter": persona(80, True),
                              "ai_systems_rep": persona(80, True)}}
        ppath = os.path.join(ws, "panel.json")
        json.dump(panel, open(ppath, "w"))
        p = run([os.path.join(ROOT, "skills/resume-grader/scripts/aggregate.py"), ppath])
        ok = p.returncode == 0
        check("aggregate.py runs", ok, (p.stderr or "")[-160:].strip())
        if ok:
            try:
                agg = json.loads(p.stdout)
                # vote-coupling: a would-interview persona floors at 85
                check("vote-coupling floors a yes-vote persona at 85",
                      agg.get("panel_avg", 0) >= 85, f"panel_avg={agg.get('panel_avg')}")
                check("counts all three interview votes",
                      agg.get("interview_votes") == 3, f"votes={agg.get('interview_votes')}")
                check("non-reach employer passes at >= 70",
                      agg.get("overall_pass") is True, f"pass={agg.get('overall_pass')} thr={agg.get('threshold')}")
            except json.JSONDecodeError as e:
                check("aggregate.py emits valid JSON", False, str(e))

        # 5. The dashboard serves, and the Start Here walkthrough tracks progress.
        print("\n5. dashboard + Start Here walkthrough")
        import urllib.request
        env = dict(os.environ, RECRUIT_HOME=ws, RECRUIT_DASH_PORT="8894")
        srv = subprocess.Popen([PY, os.path.join(ROOT, "dashboard/server.py")],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            import time
            time.sleep(1.5)
            def get(path):
                with urllib.request.urlopen(f"http://127.0.0.1:8894{path}", timeout=10) as r:
                    return json.loads(r.read())
            setup = get("/api/setup")
            check("/api/setup responds", isinstance(setup.get("steps"), list),
                  f"{setup.get('done')}/{setup.get('total')} steps done")
            check("walkthrough sees the built resume",
                  any(s["n"] == 4 and s["done"] for s in setup.get("steps", [])), "")
            alld = get("/api/all")
            check("/api/all responds with every tab's data", len(alld) >= 5, f"{len(alld)} sections")
            for tab in ("setup", "jobs", "goals", "resumes", "system"):
                check(f"  tab data: {tab}", tab in alld, "")
            with urllib.request.urlopen("http://127.0.0.1:8894/", timeout=10) as r:
                html = r.read().decode()
            check("index.html serves with Start Here", "Start Here" in html, "")
        finally:
            srv.terminate()
            srv.wait(timeout=10)
    finally:
        shutil.rmtree(ws, ignore_errors=True)

    failed = [r for r in results if r[0] == FAIL]
    print(f"\n{'=' * 56}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("\nFAILED:")
        for _, name, detail in failed:
            print(f"  - {name} {detail}")
        return 1
    print("All good. A fresh clone works end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
