#!/usr/bin/env python3
"""job_scout - ingest roles from public ATS JSON endpoints (Greenhouse boards-api +
Ashby posting-api, both public, no auth, ToS-clean), score them, select the top N
per company, and capture the JD text for the selected roles. Writes
state/jobs.json (Jobs tab) + state/review-candidates.json (review flow).

Edit workspace/state/target_companies.json to set YOUR target boards (each row is
{name, ats: greenhouse|ashby, token}) and criteria. Run: python3 job_scout.py
"""
import argparse, html, json, os, re, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
HOME = os.environ.get("RECRUIT_HOME", os.path.join(PLUGIN_ROOT, "workspace"))
STATE = os.path.join(HOME, "state")
CFG = os.path.join(STATE, "target_companies.json")
JOBS_OUT = os.path.join(STATE, "jobs.json")
REVIEW_OUT = os.path.join(STATE, "review-candidates.json")

DEFAULT_COMPANIES = [
    {"name": "Anthropic", "ats": "greenhouse", "token": "anthropic"},
    {"name": "OpenAI", "ats": "ashby", "token": "openai"},
    {"name": "Databricks", "ats": "greenhouse", "token": "databricks"},
    {"name": "Scale AI", "ats": "greenhouse", "token": "scaleai"},
    {"name": "xAI", "ats": "greenhouse", "token": "xai"},
    {"name": "Cohere", "ats": "ashby", "token": "cohere"},
    {"name": "Sierra", "ats": "ashby", "token": "sierra"},
]
CRITERIA = {"comp_min": 350000, "target": "Applied AI Architect / Forward-Deployed Engineer / Solutions Architect", "min_match": 55}
STRONG = ("applied ai", "forward deployed", "forward-deployed", "solutions architect", "solutions engineer",
          "ai architect", "technical account manager", "field engineer", "deployment engineer",
          "customer engineer", "developer experience", "member of technical staff", "solutions consultant")
MEDIUM = ("ai engineer", "machine learning engineer", "ml engineer", "sales engineer", "developer relations",
          "developer advocate", "product engineer", "platform engineer", "technical lead", "gtm engineer",
          "prototype", "customer success engineer")
SENIOR = ("senior", "staff", "principal", "lead", "head of", "director", "architect")
JUNIOR = ("intern", "new grad", "early career", "apprentice", "university", "phd")
_PAY_RE = re.compile(r"\$\s?(\d{3},\d{3})(?:\s*(?:-|to|—|–)\s*\$?\s?(\d{3},\d{3}))?")


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "recruit-copilot-jobscout/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def score_job(title, location):
    t = (title or "").lower()
    if any(k in t for k in STRONG):
        s = 78
    elif any(k in t for k in MEDIUM):
        s = 58
    elif "engineer" in t or "architect" in t or "solutions" in t:
        s = 38
    else:
        s = 12
    if any(k in t for k in SENIOR):
        s += 12
    if any(k in t for k in JUNIOR):
        s -= 30
    if any(k in t for k in ("ai", "ml", "llm", "genai", "generative", "claude", "gpt")):
        s += 5
    loc = (location or "").lower()
    if any(k in loc for k in ("remote", "united states", "san francisco", "new york", "seattle", "us", "bay area")):
        s += 3
    return max(0, min(100, s))


def _comp_from_text(text):
    for m in _PAY_RE.finditer(text or ""):
        lo, hi = m.group(1), m.group(2)
        if int(lo.replace(",", "")) >= 100000:
            return f"${lo}" + (f" - ${hi}" if hi else "")
    return None


# ---- ATS adapters: normalize to {title, location, url, id, raw_jd_fetch()} ----
def fetch_greenhouse(token):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    out = []
    for j in data.get("jobs", []):
        out.append({"title": j.get("title", ""), "location": (j.get("location") or {}).get("name", ""),
                    "url": j.get("absolute_url", ""), "id": j.get("id"), "ats": "greenhouse", "token": token,
                    "jd_text": None})
    return out


def fetch_ashby(org):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{org}")
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        out.append({"title": j.get("title", ""), "location": j.get("location", ""),
                    "url": j.get("jobUrl", ""), "id": j.get("id"), "ats": "ashby", "token": org,
                    "jd_text": j.get("descriptionPlain") or None})  # Ashby ships the JD inline
    return out


def hydrate_jd(job):
    """Ensure job['jd_text'] is populated (Ashby already has it; Greenhouse fetch content)."""
    if job.get("jd_text"):
        return job
    if job["ats"] == "greenhouse":
        try:
            d = _get(f"https://boards-api.greenhouse.io/v1/boards/{job['token']}/jobs/{job['id']}?content=true")
            job["jd_text"] = html.unescape(re.sub(r"<[^>]+>", " ", d.get("content", "")))
        except Exception:
            job["jd_text"] = ""
    return job


def scout(per_company=5, min_match=None):
    companies = DEFAULT_COMPANIES
    if os.path.exists(CFG):
        try:
            companies = json.load(open(CFG)).get("companies", DEFAULT_COMPANIES)
        except Exception:
            pass
    min_match = min_match if min_match is not None else CRITERIA["min_match"]
    flat, review, sources = [], [], []
    for c in companies:
        try:
            jobs = fetch_ashby(c["token"]) if c["ats"] == "ashby" else fetch_greenhouse(c["token"])
        except Exception as e:
            sources.append({"company": c["name"], "ok": False, "error": str(e)})
            continue
        for j in jobs:
            j["company"] = c["name"]
            j["match"] = score_job(j["title"], j["location"])
        jobs.sort(key=lambda x: x["match"], reverse=True)
        kept = [j for j in jobs if j["match"] >= min_match]
        sources.append({"company": c["name"], "ok": True, "total": len(jobs), "matched": len(kept)})
        flat.extend(kept)
        # top-N per company for the review flow -> hydrate JD + comp
        top = kept[:per_company]
        for j in top:
            hydrate_jd(j)
            j["comp"] = _comp_from_text(j.get("jd_text", ""))
        review.append({"name": c["name"], "ats": c["ats"], "token": c["token"],
                       "jobs": [{k: j[k] for k in ("title", "location", "url", "id", "ats", "token",
                                                   "match", "comp", "jd_text")} for j in top]})
    flat.sort(key=lambda x: x["match"], reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    json.dump({"generated": now, "criteria": CRITERIA,
               "sources": sources, "total_matched": len(flat), "shown": min(60, len(flat)),
               "jobs": [{k: j.get(k) for k in ("company", "title", "location", "match", "comp", "url")} for j in flat[:60]],
               "note": f"{len(flat)} roles matched across {len([s for s in sources if s.get('ok')])} boards (Greenhouse + Ashby, ToS-clean)."},
              open(JOBS_OUT, "w"), indent=2, default=str)
    json.dump({"generated": now, "per_company": per_company, "companies": review},
              open(REVIEW_OUT, "w"), indent=2, default=str)
    return {"sources": sources, "review": review, "flat": len(flat)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-company", type=int, default=5)
    ap.add_argument("--min", type=int, default=None)
    a = ap.parse_args()
    r = scout(a.per_company, a.min)
    for co in r["review"]:
        print(f"{co['name']:<12} {len(co['jobs'])} selected: " +
              ", ".join(f"{j['title'][:28]}({j['match']})" for j in co["jobs"][:3]) + " ...")
    print(f"wrote {JOBS_OUT} + {REVIEW_OUT}")
