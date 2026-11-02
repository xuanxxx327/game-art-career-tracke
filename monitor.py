"""Public-careers discovery prototype. All matches require official verification."""
import datetime
import json
import pathlib
import re
import urllib.parse
import urllib.robotparser
from scrapling.fetchers import Fetcher

ROOT = pathlib.Path(__file__).parent
ART = re.compile(r"environment|level art|world art|prop artist|3d art|material artist|场景|环境美术|地编|道具美术|材质", re.I)
INTERN = re.compile(r"intern|internship|trainee|实习|暑期项目", re.I)

def collect(company):
    url = company["careers_url"]
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https":
        return [], {"status": "invalid_url"}
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        robots.read()
        if not robots.can_fetch("GameArtCareerTracker/0.1", url):
            return [], {"status": "robots_disallowed"}
    except Exception:
        return [], {"status": "robots_unavailable"}
    page = Fetcher.get(url, timeout=20)
    status_code = getattr(page, "status", None)
    if status_code is None:
        status_code = getattr(page, "status_code", None)
    if status_code and int(status_code) >= 400:
        return [], {"status": "http_error", "http_status": status_code}
    anchors = page.css("a[href]")
    rows = []
    for a in anchors:
        title = " ".join(a.css("::text").getall()).strip()
        link = urllib.parse.urljoin(url, a.attrib.get("href", ""))
        if ART.search(title) and urllib.parse.urlparse(link).scheme == "https":
            rows.append({
                "company": company["name"], "title": title[:250], "url": link,
                "status": "candidate_unverified",
                "internship_signal": bool(INTERN.search(title)),
                "eligibility": "unknown", "location": None, "deadline": None
            })
    return rows, {"status": "fetched", "http_status": status_code, "anchors_scanned": len(anchors), "art_related_links": len(rows)}

def main():
    companies = json.loads((ROOT / "companies.json").read_text(encoding="utf-8"))
    jobs, diagnostics = [], []
    for company in companies:
        try:
            rows, info = collect(company)
            jobs.extend(rows)
            diagnostics.append({"company": company["name"], **info, "candidates": len(rows)})
        except Exception as exc:
            diagnostics.append({"company": company["name"], "status": "fetch_exception", "error_type": type(exc).__name__, "candidates": 0})
    jobs = list({row["url"]: row for row in jobs}.values())
    (ROOT / "results.json").write_text(json.dumps({
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "jobs": jobs, "diagnostics": diagnostics,
        "warning": "These are unverified art-related links, not confirmed internship openings. Zero matches does not mean no vacancies."
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Checked {len(companies)} companies; {len(jobs)} unverified art-related links")

if __name__ == "__main__":
    main()
