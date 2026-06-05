"""
Indeed job scraper.

Strategy:
  1. GET the search page with `sort=date&fromage=3` (last 72 hours).
  2. Parse job cards from the HTML — targets `data-jk` attributes which Indeed
     has used consistently for job keys.
  3. For each job key, fetch the viewjob page and pull the full description from
     either structured JSON-LD (preferred, most reliable) or a fallback div.

Indeed is friendlier to scrapers than LinkedIn and their data is publicly
accessible, but their HTML still changes. The JSON-LD fallback is particularly
stable because it's SEO-driven and rarely removed.
"""

import html
import json
import random
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

SOURCE = "Indeed"

SEARCH_URL = "https://www.indeed.com/jobs"
VIEW_URL = "https://www.indeed.com/viewjob"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _sleep():
    time.sleep(random.uniform(2.5, 5.0))


def _txt(node) -> str:
    return node.get_text(strip=True) if node else ""


def _search(keywords: str, location: str, want: int) -> list[dict]:
    params = {
        "q": keywords,
        "l": location,
        "sort": "date",
        "fromage": "3",     # posted in the last 3 days
        "limit": str(want * 3),  # fetch extra; some cards are ads / duplicates
    }
    try:
        resp = requests.get(
            SEARCH_URL, params=params, headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [Indeed] search request failed: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strategy 1: cards with data-jk attribute (Indeed job key)
    cards = soup.find_all(attrs={"data-jk": True})

    # Strategy 2: job_seen_beacon containers (common class)
    if not cards:
        cards = soup.find_all(class_="job_seen_beacon")

    jobs: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        jk = card.get("data-jk") or (
            card.find(attrs={"data-jk": True}) or {}
        ).get("data-jk")
        if not jk or jk in seen:
            continue
        seen.add(jk)

        # Title — try multiple selectors
        title_node = (
            card.find("span", attrs={"title": True})
            or card.find("h2", class_=lambda c: c and "title" in c)
            or card.find("a", attrs={"data-jk": jk})
        )
        title = (
            title_node.get("title") or _txt(title_node)
            if title_node else ""
        )

        # Company
        company_node = card.find(
            "span", class_=lambda c: c and "companyName" in (c or "")
        ) or card.find(attrs={"data-testid": "company-name"})
        company = _txt(company_node)

        # Location
        loc_node = card.find(
            "div", class_=lambda c: c and "companyLocation" in (c or "")
        ) or card.find(attrs={"data-testid": "text-location"})
        loc = _txt(loc_node)

        # Date — from relative time spans or metadata
        date_node = card.find("span", class_=lambda c: c and "date" in (c or "").lower())
        date = _txt(date_node)

        if not (jk and title):
            continue

        jobs.append(
            {
                "id": f"in-{jk}",
                "title": title,
                "company": company or "Unknown",
                "location": loc,
                "date": date,
                "url": f"https://www.indeed.com/viewjob?jk={jk}",
                "source": SOURCE,
            }
        )
        if len(jobs) >= want:
            break

    return jobs


def _description(jk: str) -> str:
    """Fetch the full description for one Indeed job key."""
    try:
        resp = requests.get(
            VIEW_URL, params={"jk": jk}, headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strategy 1: JSON-LD structured data (most stable — SEO-required)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle list or single dict
            if isinstance(data, list):
                data = next(
                    (d for d in data if d.get("@type") == "JobPosting"), {}
                )
            if data.get("@type") == "JobPosting" and data.get("description"):
                raw = data["description"]
                # Strip HTML tags that appear inside the JSON value
                return BeautifulSoup(raw, "html.parser").get_text(
                    separator="\n", strip=True
                )
        except (json.JSONDecodeError, AttributeError):
            continue

    # Strategy 2: well-known description div
    node = soup.find(id="jobDescriptionText") or soup.find(
        class_="jobsearch-jobDescriptionText"
    )
    if node:
        return html.unescape(node.get_text(separator="\n", strip=True))

    return ""


def scrape(keywords: str, location: str, want: int) -> list[dict]:
    print(f"  [Indeed] searching: {keywords} | {location}")
    jobs = _search(keywords, location, want)
    print(f"  [Indeed] {len(jobs)} card(s) found, fetching descriptions…")
    for job in jobs:
        _sleep()
        raw_jk = job["id"].removeprefix("in-")
        job["description"] = _description(raw_jk)
    return [j for j in jobs if j["description"]]
