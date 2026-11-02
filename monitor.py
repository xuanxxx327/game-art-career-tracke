"""Public-careers prototype. Results are unverified candidates."""
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
        return [], "invalid_url"
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        robots.read()
        if not robots.can_fetch("GameArtCareerTracker/0.1", url):
            return [], "robots_disallowed"
    except Exception:
        return [], "robots_unavailable"
    page = Fetcher.get(url, timeout=20)
    rows = []
    for a in page.css("a[href]"):
        title = " ".join(a.css("::text").getall()).strip()
        link = urllib.parse.urljoin(url, a.attrib.get("href", ""))
        if ART.search(title) and INTERN.search(title) and urllib.parse.urlparse(link).scheme == "https":
            rows.append({"company": company["name"], "title": title[:250], "url": link, "status": "candidate_unverified", "eligibility": "unknown", "location": None, "deadline": None})
    return rows, "ok"

def main():
    companies = json.loads((ROOT / "companies.json").read_text(encoding="utf-8"))
    jobs, diagnostics = [], []
    for company in companies:
        try:
            rows, status = collect(company)
            jobs.extend(rows)
            diagnostics.append({"company": company["name"], "status": status, "candidates": len(rows)})
        except Exception as exc:
            diagnostics.append({"company": company["name"], "status": type(exc).__name__, "candidates": 0})
    jobs = list({row["url"]: row for row in jobs}.values())
    (ROOT / "results.json").write_text(json.dumps({"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "jobs": jobs, "diagnostics": diagnostics}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Checked {len(companies)} companies; {len(jobs)} unverified candidates")

if __name__ == "__main__":
    main()
