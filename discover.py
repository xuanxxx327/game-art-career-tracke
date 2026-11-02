"""Conservative public-ATS discovery. Candidates are never enabled without brand verification.
Runs in GitHub Actions, rotating through an on-repo watchlist in small batches.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse, unquote

import requests

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources.json"
STATE = ROOT / "data" / "discovery_state.json"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "GameArtCareerTracker/0.5 (personal public careers research)"
TIMEOUT = 9
MAX_WORKERS = 6
MAX_BATCH = int(os.environ.get("DISCOVERY_BATCH_SIZE", "35"))
ATS = {
    "greenhouse": ("https://job-boards.greenhouse.io/{slug}", "job-boards.greenhouse.io"),
    "lever": ("https://jobs.lever.co/{slug}", "jobs.lever.co"),
    "ashby": ("https://jobs.ashbyhq.com/{slug}", "jobs.ashbyhq.com"),
    "smartrecruiters": ("https://careers.smartrecruiters.com/{slug}", "careers.smartrecruiters.com"),
    "workable": ("https://apply.workable.com/{slug}/", "apply.workable.com"),
}
# Avoid collisions with unrelated companies for short/ambiguous names.
MIN_NAME_LENGTH = 7


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.title += data


def brand(s):
    return re.sub(r"[^a-z0-9]+", "", s.casefold())


def slugs(name):
    if not name or re.search(r"[^A-Za-z0-9 \-&.']", name):
        return []
    words = re.findall(r"[a-z0-9]+", name.lower())
    if not words or len("".join(words)) < MIN_NAME_LENGTH:
        return []
    variants = ["".join(words), "-".join(words)]
    # Only drop common suffixes when at least two distinctive tokens remain.
    if len(words) >= 3 and words[-1] in ("games", "studios", "studio", "entertainment", "interactive"):
        variants.append("".join(words[:-1]))
        variants.append("-".join(words[:-1]))
    return list(dict.fromkeys(variants))


def strong_identity(name, page_title):
    """Never infer a source merely from a valid slug or HTTP 200."""
    actual = brand(name)
    title = brand(re.sub(r"\b(jobs|careers|open positions|at|join|hiring)\b", " ", page_title, flags=re.I))
    return len(actual) >= MIN_NAME_LENGTH and actual in title


def get(url):
    response = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    return response


def verified_board(company, kind, slug):
    template, hostname = ATS[kind]
    url = template.format(slug=slug)
    response = get(url)
    if urlparse(response.url).hostname != hostname:
        return None
    page = TextParser()
    page.feed(response.text[:600000])
    if not strong_identity(company, page.title):
        return None
    return {"source": kind, "slug": slug, "homepage": url,
            "verification": "public_board_title"}


def official_link(source):
    """Follow ATS links found on a known official careers homepage only."""
    homepage = source.get("homepage") or ""
    if not homepage.startswith("https://"):
        return None
    host = urlparse(homepage).hostname or ""
    if host in (item[1] for item in ATS.values()):
        return None
    response = get(homepage)
    page = TextParser()
    page.feed(response.text[:800000])
    for raw in page.links:
        link = unquote(raw)
        if link.startswith("//"):
            link = "https:" + link
        if link.startswith("/"):
            continue
        if not link.startswith("https://"):
            continue
        parsed = urlparse(link)
        for kind, (_, hostname) in ATS.items():
            if parsed.hostname == hostname:
                slug = parsed.path.strip("/").split("/")[0]
                if re.fullmatch(r"[A-Za-z0-9_-]{3,64}", slug):
                    # The employer itself linked this ATS from its official page.
                    return {"source": kind, "slug": slug, "homepage": link,
                            "verification": "linked_from_official_careers_page"}
    return None


def discover_one(source):
    try:
        found = official_link(source)
        if found:
            return source["name"], found, None
    except requests.RequestException:
        pass
    for slug in slugs(source["name"]):
        for kind in ATS:
            try:
                found = verified_board(source["name"], kind, slug)
                if found:
                    return source["name"], found, None
            except (requests.RequestException, ValueError):
                continue
    return source["name"], None, "not_verifiable"


def main():
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"attempts": {}}
    attempts = state.setdefault("attempts", {})
    candidates = [s for s in sources if s.get("source") == "links"]
    # Round robin: never let all 200+ sources block the daily collector.
    candidates.sort(key=lambda s: (attempts.get(s["name"], {}).get("checked_at", ""),
                                    s.get("priority", 9), s["name"]))
    batch = candidates[:MAX_BATCH]
    timestamp = datetime.now(timezone.utc).isoformat()
    verified = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        jobs = {pool.submit(discover_one, source): source for source in batch}
        for future in as_completed(jobs):
            source = jobs[future]
            try:
                name, result, error = future.result()
            except Exception as exc:
                name, result, error = source["name"], None, type(exc).__name__
            attempts[name] = {"checked_at": timestamp, "result": "verified" if result else error}
            if result:
                source.update(result)
                verified.append({"company": name, "source": result["source"],
                                 "slug": result["slug"], "verification": result["verification"]})
    SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state["checked_at"] = timestamp
    state["checked_this_run"] = len(batch)
    state["new_verified_this_run"] = verified
    state["watchlist_size"] = len(sources)
    state["configured_sources"] = sum(s.get("source") != "links" for s in sources)
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scanned": len(batch), "verified_new": verified,
                      "configured_sources": state["configured_sources"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
