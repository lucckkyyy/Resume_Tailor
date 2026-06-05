"""
LinkedIn job scraper — public guest endpoint, no login required.

Filters to internship/co-op job types AND the last 24 hours so you only get
fresh listings. Uses the same endpoints a logged-out browser sees.

CAVEATS: Automated access violates LinkedIn's ToS. Keep MAX_JOBS_PER_SOURCE
small (<=5) and run once a day max. If results go empty, LinkedIn changed its
HTML or is rate-limiting you — the class names below are updated as of 2026
but will drift over time.
"""

import html
import random
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

SOURCE = "LinkedIn"

SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
JOB_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# LinkedIn job-type filter codes
# 'I' = Internship  (no code for co-op specifically, covered by keywords)
LI_JOB_TYPE = "I"


def _sleep():
    time.sleep(random.uniform(2.0, 4.0))


def _txt(node) -> str:
    return node.get_text(strip=True) if node else ""


def _job_id(card) -> str | None:
    urn = card.get("data-entity-urn", "")
    if urn:
        return urn.rsplit(":", 1)[-1]
    link = card.find("a", href=True)
    if link:
        for part in link["href"].split("?")[0].rstrip("/").split("-"):
            if part.isdigit() and len(part) >= 6:
                return part
    return None


def _cards(keywords: str, location: str, want: int) -> list[dict]:
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": "r259200",   # last 72 hours
        "f_JT": LI_JOB_TYPE, # internship job type
        "sortBy": "DD",
        "start": 0,
    }
    try:
        resp = requests.get(
            SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [LinkedIn] search request failed: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    raw = soup.find_all("div", class_="base-card") or soup.find_all("li")

    jobs: list[dict] = []
    for card in raw:
        job_id = _job_id(card)
        title = _txt(card.find(class_="base-search-card__title"))
        company = _txt(card.find(class_="base-search-card__subtitle"))
        loc = _txt(card.find(class_="job-search-card__location"))
        link_a = card.find("a", class_="base-card__full-link") or card.find(
            "a", href=True
        )
        url = link_a["href"].split("?")[0] if link_a else None
        time_node = card.find("time")
        date = (time_node.get("datetime", "") if time_node else "") or _txt(time_node)

        if not (job_id and title):
            continue

        jobs.append(
            {
                "id": f"li-{job_id}",
                "title": title,
                "company": company or "Unknown",
                "location": loc,
                "date": date,
                "url": url or f"https://www.linkedin.com/jobs/view/{job_id}",
                "source": SOURCE,
            }
        )
        if len(jobs) >= want:
            break

    return jobs


def _description(job_id_raw: str) -> str:
    """Fetch full job description from the per-job endpoint."""
    numeric_id = job_id_raw.removeprefix("li-")
    try:
        resp = requests.get(
            JOB_URL.format(job_id=numeric_id),
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    node = soup.find(class_="show-more-less-html__markup") or soup.find(
        class_="description__text"
    )
    return html.unescape(node.get_text(separator="\n", strip=True)) if node else ""


def scrape(keywords: str, location: str, want: int) -> list[dict]:
    print(f"  [LinkedIn] searching: {keywords} | {location}")
    jobs = _cards(keywords, location, want)
    print(f"  [LinkedIn] {len(jobs)} card(s) found, fetching descriptions…")
    for job in jobs:
        _sleep()
        job["description"] = _description(job["id"])
    return [j for j in jobs if j["description"]]
