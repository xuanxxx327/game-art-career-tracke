"""Game art openings monitor: structured ATS first; two separate recruitment tracks."""
from __future__ import annotations
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
TIMEOUT = 18
UA = "GameArtCareerTracker/0.2 (+personal research; public job board APIs)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})
ART = re.compile(r"environment|world art|level art|level artist|prop artist|3d artist|3d art|3d model|material artist|texture artist|lighting artist|technical artist|场景|环境美术|地编|道具美术|模型师|材质|灯光美术|技术美术", re.I)
INTERNSHIP = re.compile(r"intern(ship)?|trainee|placement|实习|暑期实习", re.I)
CAMPUS = re.compile(r"graduate|new grad|new graduate|entry.level|early career|campus|university grad|应届|校招|校园招聘|毕业生|管培", re.I)
SENIOR = re.compile(r"senior|staff|principal|lead|director|manager|head of|高级|资深|专家|主管|负责人|总监", re.I)
CHINA = re.compile(r"china|shanghai|beijing|guangzhou|shenzhen|chengdu|hangzhou|suzhou|wuhan|nanjing|中国|上海|北京|广州|深圳|成都|杭州|苏州|武汉|南京", re.I)

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))).strip()

def get_json(url):
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def lever(source):
    slug = source["slug"]
    raw = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if not isinstance(raw, list):
        raise ValueError("Lever response was not a list")
    for j in raw:
        cats = j.get("categories") or {}
        yield dict(
            source_id=str(j.get("id", "")),
            title=j.get("text", ""),
            location=cats.get("location", ""),
            department=cats.get("team", ""),
            employment_type=cats.get("commitment", ""),
            description=clean(j.get("descriptionPlain") or j.get("description")),
            url=j.get("hostedUrl") or j.get("applyUrl", ""),
            published_at=None,
        )

def smartrecruiters(source):
    slug = source["slug"]
    offset = 0
    for _ in range(20):
        raw = get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}")
        batch = raw.get("content", [])
        if not isinstance(batch, list):
            raise ValueError("SmartRecruiters response invalid")
        for j in batch:
            loc = j.get("location") or {}
            typ = j.get("typeOfEmployment") or {}
            yield dict(
                source_id=str(j.get("id", "")),
                title=j.get("name", ""),
                location=", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country")])),
                department=(j.get("department") or {}).get("label", ""),
                employment_type=typ.get("label", "") if isinstance(typ, dict) else str(typ),
                description="",
                url=j.get("ref") or f"https://jobs.smartrecruiters.com/{slug}/{j.get('id', '')}",
                published_at=j.get("releasedDate"),
            )
        offset += len(batch)
        if not batch or offset >= raw.get("totalFound", offset):
            break

def greenhouse(source):
    raw = get_json(f"https://boards-api.greenhouse.io/v1/boards/{source['slug']}/jobs?content=true")
    for j in raw.get("jobs", []):
        yield dict(
            source_id=str(j.get("id", "")),
            title=j.get("title", ""),
            location=(j.get("location") or {}).get("name", ""),
            department=", ".join(d.get("name", "") for d in (j.get("departments") or [])),
            employment_type="",
            description=clean(j.get("content")),
            url=j.get("absolute_url", ""),
            published_at=j.get("first_published"),
        )

def ashby(source):
    """Public Ashby job board, no private API key needed."""
    slug = source["slug"]
    raw = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    if not isinstance(raw.get("jobs"), list):
        raise ValueError("Ashby response invalid")
    for j in raw["jobs"]:
        if j.get("isListed") is False:
            continue
        yield dict(
            source_id=str(j.get("id") or j.get("jobUrl") or ""),
            title=j.get("title", ""),
            location=j.get("location", ""),
            department=j.get("department", ""),
            employment_type=j.get("employmentType", ""),
            description=clean(j.get("descriptionPlain") or j.get("descriptionHtml")),
            url=j.get("jobUrl") or j.get("applyUrl", ""),
            published_at=j.get("publishedAt"),
        )

def workable(source):
    """Public Workable widget feed."""
    raw = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{source['slug']}?details=true")
    batch = raw.get("jobs", []) if isinstance(raw, dict) else []
    if not isinstance(batch, list):
        raise ValueError("Workable jobs response invalid")
    for j in batch:
        loc = j.get("location") or {}
        if isinstance(loc, dict):
            place = ", ".join(str(v) for v in [loc.get("city"), loc.get("country")] if v)
        else:
            place = str(loc)
        yield dict(source_id=str(j.get("shortcode") or j.get("id") or ""),
                   title=j.get("title", ""), location=place,
                   department=j.get("department", ""),
                   employment_type=j.get("employment_type", ""),
                   description=clean(j.get("description", "")),
                   url=j.get("url") or j.get("application_url") or "",
                   published_at=j.get("published_on"))

def recruitee(source):
    """Public Recruitee careers API."""
    raw = get_json(f"https://{source['slug']}.recruitee.com/api/offers/")
    batch = raw.get("offers", []) if isinstance(raw, dict) else []
    if not isinstance(batch, list):
        raise ValueError("Recruitee offers response invalid")
    for j in batch:
        yield dict(source_id=str(j.get("id") or ""),
                   title=j.get("title", ""), location=j.get("location", ""),
                   department=j.get("department", ""),
                   employment_type=j.get("employment_type", ""),
                   description=clean(j.get("description", "")),
                   url=j.get("careers_url") or j.get("url") or "",
                   published_at=j.get("published_at"))

FETCHERS = {"lever": lever, "smartrecruiters": smartrecruiters, "greenhouse": greenhouse, "ashby": ashby, "workable": workable, "recruitee": recruitee}

def normalize(source, job, now):
    title = clean(job["title"])
    location = clean(job.get("location"))
    description = clean(job.get("description"))
    employment = clean(job.get("employment_type"))
    department = clean(job.get("department"))
    # Classification deliberately uses job metadata and title, NOT description
    # (descriptions frequently mention interns or graduates incidentally).
    tag = " ".join([title, employment, department])
    if not ART.search(title):
        return None
    if SENIOR.search(title):
        return None
    if INTERNSHIP.search(tag):
        track = "internship"
    elif CAMPUS.search(tag):
        track = "campus"
    else:
        # No evidence that a regular full-time role is a campus role.
        return None
    url = job.get("url", "")
    if urlparse(url).scheme != "https":
        return None
    ident = job.get("source_id") or url
    key = hashlib.sha256((source["name"] + ":" + str(ident)).encode()).hexdigest()[:24]
    overseas = not CHINA.search(location)
    eligibility = "needs_verification" if overseas else "check_job_requirements"
    eligibility_notes = ""
    # Official Larian Ghent internship application currently limits candidates to
    # the Benelux, France and Germany region. Do not recommend it as broadly eligible.
    if source["name"] == "Larian Studios" and "55238820-92ef-4b4e-ba18-a9fdd027f737" in url:
        eligibility = "restricted_region"
        eligibility_notes = "官方申请表注明目前仅接受比荷卢、法国及德国地区候选人；须以最新表单为准。"
    return {
        "id": key, "company": source["name"], "group": source["group"],
        "track": track, "title": title, "location": location or "未注明",
        "employment_type": employment, "department": department,
        "url": url, "published_at": job.get("published_at"),
        "first_seen": now, "last_seen": now, "status": "open",
        "eligibility": eligibility, "eligibility_notes": eligibility_notes,
        "description_excerpt": description[:900],
        "source_type": source["source"],
        "verified_as_intern_or_campus": True,
    }

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    previous_path = DATA / "jobs.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {"jobs": []}
    previous_jobs = {j["id"]: j for j in previous.get("jobs", [])}
    jobs = dict(previous_jobs)
    diagnostics = []
    success = 0
    for source in sources:
        fetch = FETCHERS.get(source["source"])
        if fetch is None:
            diagnostics.append({"company": source["name"], "status": "not_integrated", "reason": "Official careers API adapter still needed"})
            continue
        try:
            raw = list(fetch(source))
            fresh = [j for item in raw if (j := normalize(source, item, now))]
            ids = set()
            for job in fresh:
                ids.add(job["id"])
                if job["id"] in jobs:
                    job["first_seen"] = jobs[job["id"]].get("first_seen", now)
                jobs[job["id"]] = job
            # Only mark closed after a complete, successful response from that source.
            for key, job in jobs.items():
                if job["company"] == source["name"] and key not in ids:
                    job["status"] = "not_seen_latest_check"
            diagnostics.append({"company": source["name"], "status": "ok", "postings_scanned": len(raw), "matching": len(fresh)})
            success += 1
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            diagnostics.append({"company": source["name"], "status": "error", "error": type(exc).__name__, "detail": str(exc)[:180]})
    payload = {
        "checked_at": now, "source_success_count": success,
        "notes": "Only titles explicitly labeled internship or graduate/campus are shown. Overseas eligibility requires manual verification. not_seen_latest_check is NOT confirmed closed.",
        "jobs": sorted(jobs.values(), key=lambda j: (j["track"], j["company"], j["title"])),
        "diagnostics": diagnostics,
    }
    previous_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(sources), "successful": success, "internships": sum(j["track"] == "internship" and j["status"] == "open" for j in jobs.values()), "campus": sum(j["track"] == "campus" and j["status"] == "open" for j in jobs.values())}))
    if not success:
        print("WARNING: No structured sources succeeded. See diagnostics.", file=sys.stderr)

if __name__ == "__main__":
    main()
