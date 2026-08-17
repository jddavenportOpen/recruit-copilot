#!/usr/bin/env python3
"""job_scout - ingest roles from public ATS JSON endpoints, score each against
your criteria, and write workspace/state/jobs.json so the Jobs tab goes live.

Source: Greenhouse boards-api (public, no auth, ToS-clean):
  https://boards-api.greenhouse.io/v1/boards/{token}/jobs

Run:  python3 job_scout.py            (uses workspace/state/target_companies.json)
      python3 job_scout.py --min 60   (raise the match threshold)

Edit workspace/state/target_companies.json to set your target boards and the
title keywords that define a match for YOUR search. Stdlib only.
"""
import argparse
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
HOME = os.environ.get("RECRUIT_HOME", os.path.join(PLUGIN_ROOT, "workspace"))
STATE = os.path.join(HOME, "state")
CFG = os.path.join(STATE, "target_companies.json")
OUT = os.path.join(STATE, "jobs.json")

DEFAULT_CFG = {
    "criteria": {"comp_min": 200000, "target": "your target roles", "min_match": 55},
    "strong_titles": ["solutions architect", "solutions engineer", "forward deployed",
                      "applied ai", "ai architect", "sales engineer", "field engineer",
                      "customer engineer", "technical account manager"],
    "medium_titles": ["ai engineer", "machine learning engineer", "member of technical staff",
                     "developer relations", "product engineer", "platform engineer"],
    "companies": [
        {"name": "Anthropic", "token": "anthropic"},
        {"name": "Databricks", "token": "databricks"},
        {"name": "Scale AI", "token": "scaleai"},
        {"name": "xAI", "token": "xai"},
        {"name": "Together AI", "token": "togetherai"},
    ],
}
SENIOR = ("senior", "staff", "principal", "lead", "head of", "director", "architect")
JUNIOR = ("intern", "new grad", "early career", "apprentice", "associate", "university")


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "recruit-copilot-jobscout/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def score_job(title, location, strong, medium):
    t = (title or "").lower()
    if any(k in t for k in strong):
        score = 75
    elif any(k in t for k in medium):
        score = 55
    elif "engineer" in t or "architect" in t or "solutions" in t:
        score = 35
    else:
        score = 10
    if any(k in t for k in SENIOR):
        score += 12
    if any(k in t for k in JUNIOR):
        score -= 28
    if any(k in t for k in ("ai", "ml", "llm", "genai", "generative")):
        score += 5
    loc = (location or "").lower()
    if any(k in loc for k in ("remote", "united states", "san francisco", "new york", "seattle", "us")):
        score += 3
    return max(0, min(100, score))


_PAY_RE = re.compile(r"\$\s?(\d{3},\d{3})(?:\s*(?:-|to|—|–)\s*\$?\s?(\d{3},\d{3}))?")


def fetch_comp(token, job_id):
    try:
        d = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}?content=true")
        content = html.unescape(d.get("content", ""))
        for m in _PAY_RE.finditer(content):
            lo, hi = m.group(1), m.group(2)
            if int(lo.replace(",", "")) >= 100000:
                return f"${lo}" + (f" - ${hi}" if hi else "")
    except Exception:
        return None
    return None


def load_cfg():
    if os.path.exists(CFG):
        try:
            c = json.load(open(CFG))
            for k, v in DEFAULT_CFG.items():
                c.setdefault(k, v)
            return c
        except Exception:
            pass
    os.makedirs(STATE, exist_ok=True)
    json.dump(DEFAULT_CFG, open(CFG, "w"), indent=2)
    return DEFAULT_CFG


def scout(min_match=None, enrich_top=14):
    cfg = load_cfg()
    strong = [s.lower() for s in cfg.get("strong_titles", [])]
    medium = [s.lower() for s in cfg.get("medium_titles", [])]
    min_match = min_match if min_match is not None else cfg.get("criteria", {}).get("min_match", 55)
    all_jobs, sources, counts = [], [], {}
    for c in cfg.get("companies", []):
        token = c.get("token")
        try:
            data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
        except Exception as e:
            sources.append({"company": c["name"], "token": token, "ok": False, "error": str(e)})
            continue
        jobs = data.get("jobs", [])
        sources.append({"company": c["name"], "token": token, "ok": True, "total": len(jobs)})
        kept = 0
        for j in jobs:
            loc = (j.get("location") or {}).get("name", "")
            m = score_job(j.get("title", ""), loc, strong, medium)
            if m < min_match:
                continue
            all_jobs.append({"company": c["name"], "token": token, "id": j.get("id"),
                             "title": j.get("title", ""), "location": loc, "match": m,
                             "url": j.get("absolute_url", ""), "updated": (j.get("updated_at") or "")[:10], "comp": None})
            kept += 1
        counts[c["name"]] = {"total": len(jobs), "matched": kept}
    all_jobs.sort(key=lambda x: x["match"], reverse=True)
    for job in all_jobs[:enrich_top]:
        job["comp"] = fetch_comp(job["token"], job["id"])
    payload = {"generated": datetime.now(timezone.utc).isoformat(), "criteria": cfg.get("criteria", {}),
               "sources": sources, "counts": counts, "total_matched": len(all_jobs),
               "shown": min(60, len(all_jobs)), "jobs": all_jobs[:60],
               "note": f"{len(all_jobs)} roles matched across {len([s for s in sources if s.get('ok')])} boards "
                       f"(threshold {min_match}); top {min(60, len(all_jobs))} shown. Public Greenhouse API, ToS-clean."}
    os.makedirs(STATE, exist_ok=True)
    json.dump(payload, open(OUT, "w"), indent=2, default=str)
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=None)
    p = scout(ap.parse_args().min)
    ok = [s for s in p["sources"] if s.get("ok")]
    print(f"scouted {len(ok)} boards -> {p['total_matched']} matched, top {len(p['jobs'])} shown")
    for j in p["jobs"][:10]:
        print(f"  {j['match']:>3}  {j['company']:<12} {j['title'][:50]:<50} {j['comp'] or ''}")
    print(f"wrote {OUT}")
