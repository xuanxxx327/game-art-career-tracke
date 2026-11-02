# Game Art Career Tracker · 游戏美术招聘监控

A mobile-friendly job tracker with **two distinct tabs**: **实习岗位 / Internships** and **校招岗位 / Campus / New Graduate**.

## Status
- The cloud workflow and responsive dashboard are committed to this repository.
- Structured ATS integrations: **Larian Studios (Lever)** and **Keywords Studios (SmartRecruiters)**. These are real, public ATS endpoints; live availability is not guaranteed.
- Other studios are on a watchlist and are **not yet integrated**. They are not reported as having zero openings.
- Overseas internships are **not automatically assumed eligible** for Chinese students.
- The initial job dataset is empty until a successful GitHub Actions run.
- No Supabase integration, automatic push notification, or verified production deployment yet.

## Run

GitHub Actions → **Game Art Career Monitor** → **Run workflow**. The scheduled job is configured for 01:20 UTC / 09:20 Beijing time; actual start may be delayed.

After each run, open `data/jobs.json` in the repo or download the `recruitment-results` artifact. The workflow also commits its latest snapshot to the repository.

## Dashboard

The static dashboard is `index.html`. To make it accessible on phone and desktop, configure **Settings → Pages → Build and deployment → Source: GitHub Actions**. Then run **Publish Career Dashboard**. This is a public, read-only dashboard because the repository is currently public. **Do not put personal data or secrets into jobs.json.**

## Data rules
- `track: internship` requires an internship signal in the title, work type or department.
- `track: campus` requires a graduate/campus signal in the title, work type or department.
- Generic full-time roles are not mislabeled campus recruitment.
- Senior/lead/manager roles are filtered out.
- Overseas eligibility remains `needs_verification` until official conditions are reviewed.
- An absent posting after a successful scan is `not_seen_latest_check`, not confirmed closed.
- A source with no adapter is `not_integrated`, not zero vacancies.
- The system prefers official ATS endpoints over scraping. It does not circumvent robots.txt, login barriers or bot controls.

## Next improvements

Add validated official ATS adapters for more Chinese subsidiaries, Tencent studios, NetEase, miHoYo and domestic mid-size studios; distinguish internship start dates, campus cohorts and deadlines; add optional notification delivery with authorized credentials.

References: Greenhouse Job Board API, Lever public postings API, SmartRecruiters public postings API. Scrapling can be added as a fallback for compliant public HTML pages, but it is **not currently used in the structured-API monitor**.
