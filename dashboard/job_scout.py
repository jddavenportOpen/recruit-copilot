#!/usr/bin/env python3
"""job_scout - ingest roles from public ATS JSON endpoints (Greenhouse boards-api +
Ashby posting-api, both public, no auth, ToS-clean), score them, select the top N
per company, and capture the JD text for the selected roles. Writes
state/jobs.json, which the Jobs tab reads.

Edit <workspace>/state/target_companies.json to set YOUR target boards (each row is
{name, ats: greenhouse|ashby, token}) and criteria. Run: python3 job_scout.py
"""
import argparse, html, json, os, re, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
import search_goals

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
# One resolver for the whole product. This module used to default to the plugin's
# own workspace/ while the dashboard defaulted to ~/.recruit-copilot, so a user who
# never set RECRUIT_HOME had the scout write jobs into the versioned plugin
# directory and the Jobs tab read an empty one three feet away.
HOME = paths.home(create=True)
STATE = os.path.join(HOME, "state")
CFG = os.path.join(STATE, "target_companies.json")
JOBS_OUT = os.path.join(STATE, "jobs.json")

DEFAULT_COMPANIES = [
    {"name": "Anthropic", "ats": "greenhouse", "token": "anthropic"},
    {"name": "OpenAI", "ats": "ashby", "token": "openai"},
    {"name": "Databricks", "ats": "greenhouse", "token": "databricks"},
    {"name": "Scale AI", "ats": "greenhouse", "token": "scaleai"},
    {"name": "xAI", "ats": "greenhouse", "token": "xai"},
    {"name": "Cohere", "ats": "ashby", "token": "cohere"},
    {"name": "Sierra", "ats": "ashby", "token": "sierra"},
]
# Scoring comes from YOUR goals file, not from constants in here. See
# dashboard/search_goals.py for why that matters.

def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "recruit-copilot-jobscout/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def score_job(title, location, search, jd_text=""):
    """Delegates to the goals-driven scorer so the Jobs tab reflects your search."""
    return search_goals.score(title, location, search, jd_text)


def _comp_from_text(text):
    """Display string for the Jobs tab, from the same parser the scorer uses."""
    band = search_goals.pay_band(text)
    return band[2] if band else None


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


def _plain(content: str) -> str:
    """Greenhouse ships the posting body as HTML-ESCAPED HTML, so unescaping has to
    come first. Stripping tags before unescaping finds no tags to strip -- there are
    no literal angle brackets yet -- and the unescape then turns the entities INTO
    markup. Every Greenhouse posting was reaching the tailoring and grading steps as
    a wall of div, h2, li and strong, which is what those steps were matching the
    resume's keywords against."""
    text = content or ""
    for _ in range(3):                       # some entities arrive double escaped
        once = html.unescape(text)
        if once == text:
            break
        text = once
    text = re.sub(r"<[^>]+>", " ", text).replace("\u00a0", " ")
    return re.sub(r"[ \t]*\n\s*\n\s*", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def hydrate_jd(job):
    """Ensure job['jd_text'] is populated (Ashby already has it; Greenhouse fetch content)."""
    if job.get("jd_text"):
        return job
    if job["ats"] == "greenhouse":
        try:
            d = _get(f"https://boards-api.greenhouse.io/v1/boards/{job['token']}/jobs/{job['id']}?content=true")
            job["jd_text"] = _plain(d.get("content", ""))
        except Exception:
            job["jd_text"] = ""
    return job


def scout(per_company=5, min_match=None):
    """Two passes, on purpose.

    Titles and locations are free to score, but pay is only in the posting body,
    which costs a fetch per role. So: score on title first, keep what survives,
    fetch the body for the top few per company, then re-score those WITH the pay
    so the comp floor you set actually moves the number instead of being decorative.
    """
    search = search_goals.load(STATE)          # raises NoGoals; the caller must stop

    companies = DEFAULT_COMPANIES
    if os.path.exists(CFG):
        try:
            companies = json.load(open(CFG)).get("companies", DEFAULT_COMPANIES)
        except Exception:
            pass
    min_match = min_match if min_match is not None else int(search.get("min_match", 55))

    flat, review, sources = [], [], []
    for c in companies:
        # Be forgiving about the row shape: a hand-written config that omits "ats"
        # means Greenhouse (the common case), and a missing token is a config error
        # the user must be told about plainly, not a bare KeyError swallowed below.
        name = c.get("name") or c.get("token") or "(unnamed)"
        token = c.get("token")
        ats = (c.get("ats") or "greenhouse").strip().lower()
        if not token:
            sources.append({"company": name, "ok": False,
                            "error": 'missing "token" — add the board token, e.g. {"name": "Acme", "token": "acme"}'})
            continue
        if ats not in ("greenhouse", "ashby"):
            sources.append({"company": name, "ok": False,
                            "error": f'unknown ats "{ats}" — use "greenhouse" or "ashby"'})
            continue
        try:
            jobs = fetch_ashby(token) if ats == "ashby" else fetch_greenhouse(token)
        except Exception as e:
            sources.append({"company": name, "ok": False, "error": str(e)})
            continue
        for j in jobs:
            j["company"] = name
            j["match"], j["why"] = score_job(j["title"], j["location"], search)
        jobs.sort(key=lambda x: x["match"], reverse=True)
        kept = [j for j in jobs if j["match"] >= min_match]
        sources.append({"company": name, "ok": True, "total": len(jobs), "matched": len(kept)})

        top = kept[:per_company]
        for j in top:
            hydrate_jd(j)
            j["comp"] = _comp_from_text(j.get("jd_text", ""))
            # second pass: the posting body is here now, so pay can count
            j["match"], j["why"] = score_job(j["title"], j["location"], search, j.get("jd_text", ""))
        top.sort(key=lambda x: x["match"], reverse=True)
        flat.extend(kept)
        review.append({"name": name, "ats": ats, "token": token,
                       "jobs": [{k: j.get(k) for k in ("title", "location", "url", "id", "ats", "token",
                                                       "match", "why", "comp", "jd_text")} for j in top]})

    flat.sort(key=lambda x: x["match"], reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    json.dump({"generated": now, "search": search,
               "sources": sources, "total_matched": len(flat), "shown": min(60, len(flat)),
               "jobs": [dict({k: j.get(k) for k in ("company", "title", "location",
                                                     "match", "why", "comp", "url")},
                             # the posting body, for the roles deep enough to have been
                             # hydrated, so /recruit:tailor has something to tailor TO
                             # instead of asking the user to paste it back in
                             jd_text=(j.get("jd_text") or "")[:12000] or None)
                        for j in flat[:60]],
               "note": f"{len(flat)} roles matched across {len([s for s in sources if s.get('ok')])} boards (Greenhouse + Ashby, ToS-clean), scored against your goals."},
              open(JOBS_OUT, "w"), indent=2, default=str)
    return {"sources": sources, "review": review, "flat": len(flat)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-company", type=int, default=5)
    ap.add_argument("--min", type=int, default=None)
    a = ap.parse_args()
    try:
        r = scout(a.per_company, a.min)
    except search_goals.NoGoals as e:
        print(f"\n{e}\n", file=sys.stderr)
        sys.exit(2)
    for co in r["review"]:
        print(f"{co['name']:<12} {len(co['jobs'])} selected: " +
              ", ".join(f"{j['title'][:28]}({j['match']})" for j in co["jobs"][:3]) + " ...")

    # A board that failed is not a board with no matches. Say so, loudly, or a typo'd
    # token looks exactly like "this company is not hiring".
    failed = [s_ for s_ in r["sources"] if not s_.get("ok")]
    ok = [s_ for s_ in r["sources"] if s_.get("ok")]
    for s_ in failed:
        print(f"FAILED {s_['company']}: {s_.get('error','')}", file=sys.stderr)
    if not ok:
        print(f"\nNo board could be read ({len(failed)} failed). Check the tokens in "
              f"{CFG}, or your network connection.", file=sys.stderr)
        sys.exit(1)
    if failed:
        print(f"({len(failed)} of {len(r['sources'])} boards failed - see above)", file=sys.stderr)
    print(f"wrote {JOBS_OUT}")
