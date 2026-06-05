"""
Handshake job scraper — requires an authenticated session cookie.

WHY COOKIES INSTEAD OF USERNAME/PASSWORD:
Handshake uses your university's SSO (Shibboleth, Google, Microsoft, etc.) to
log students in. That SSO chain is impossible to automate reliably without a
headless browser. The practical solution: you log in once manually, copy your
session cookies, and store them as a secret. They're valid for ~30 days; you
renew them once a month (2 minutes of work).

HOW TO GET YOUR COOKIES (one-time, takes ~2 minutes):
  1. Open Chrome/Firefox, log into https://app.joinhandshake.com
  2. Open DevTools (F12) → Application → Storage → Cookies → joinhandshake.com
  3. Find `_handshake_session` — copy its VALUE (long base64 string).
     Also copy `remember_user_token` if present.
  4. Build a cookie string: "_handshake_session=VALUE; remember_user_token=VALUE"
  5. Save that string as the GitHub Secret: HANDSHAKE_SESSION_COOKIE
  6. Also save HANDSHAKE_EMAIL (your .edu address) — used as a request header.

  Tip: Use the browser extension "EditThisCookie" (Chrome) or "Cookie Quick
  Manager" (Firefox) for easier exporting.

WHEN TO RENEW: When you stop getting Handshake results, your session expired.
Log in again, copy fresh cookies, update the GitHub Secret.

This module is OPTIONAL: if HANDSHAKE_SESSION_COOKIE is not set, it returns an
empty list and the workflow carries on with LinkedIn + Indeed only.
"""

import json
import os
import random
import re
import time

import requests
from bs4 import BeautifulSoup

SOURCE = "Handshake"

SEARCH_URL = "https://app.joinhandshake.com/stu/postings"
API_URL = "https://app.joinhandshake.com/api/v0/job_postings"
JOB_URL = "https://app.joinhandshake.com/stu/postings/{posting_id}"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://app.joinhandshake.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


def _sleep():
    time.sleep(random.uniform(2.0, 4.0))


def _session(cookie_str: str, email: str) -> requests.Session:
    sess = requests.Session()
    sess.headers.update(BASE_HEADERS)
    if email:
        sess.headers["X-User-Email"] = email
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            sess.cookies.set(name.strip(), value.strip(), domain=".joinhandshake.com")
    return sess


def _extract_csrf(html_text: str) -> str | None:
    """Pull the CSRF token Handshake embeds in meta tags."""
    soup = BeautifulSoup(html_text, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    return meta.get("content") if meta else None


def _api_search(sess: requests.Session, keywords: str, want: int) -> list[dict]:
    """Try Handshake's internal JSON API first (React SPA backend)."""
    params = {
        "job_type_names[]": ["Internship", "Co-op"],
        "sort_column": "created_at",
        "sort_direction": "desc",
        "per_page": str(want * 2),
        "page": "1",
        "keywords": keywords,
    }
    headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
    try:
        resp = sess.get(API_URL, params=params, headers=headers, timeout=30)
    except requests.RequestException as exc:
        print(f"  [Handshake] API call failed: {exc}")
        return []

    if resp.status_code != 200 or "application/json" not in resp.headers.get(
        "Content-Type", ""
    ):
        return []   # Fall through to HTML scraping

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return []

    # Handshake API response shape (may vary):
    # {"job_postings": [...], "total": N}
    # or {"postings": [...]}
    postings = data.get("job_postings") or data.get("postings") or []
    jobs = []
    for p in postings[:want]:
        pid = str(p.get("id") or p.get("job_posting_id") or "")
        title = p.get("title") or p.get("position") or ""
        employer = (
            (p.get("employer") or {}).get("name")
            or p.get("employer_name")
            or "Unknown"
        )
        loc = p.get("location") or p.get("city") or ""
        date = p.get("created_at") or p.get("posted_at") or ""
        description = (
            p.get("description")
            or p.get("job_description")
            or p.get("full_description")
            or ""
        )
        if pid and title:
            jobs.append(
                {
                    "id": f"hs-{pid}",
                    "title": title,
                    "company": employer,
                    "location": loc,
                    "date": str(date)[:10],
                    "url": JOB_URL.format(posting_id=pid),
                    "description": description,
                    "source": SOURCE,
                }
            )
    return jobs


def _html_search(sess: requests.Session, keywords: str, want: int) -> list[dict]:
    """Fallback: parse the Handshake search page HTML / embedded JSON."""
    params = {
        "page": "1",
        "sort_direction": "desc",
        "sort_column": "created_at",
        "job_type_names[]": ["Internship", "Co-op"],
        "keywords": keywords,
    }
    try:
        resp = sess.get(SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [Handshake] HTML search failed: {exc}")
        return []

    if resp.url and "login" in resp.url.lower():
        print("  [Handshake] Redirected to login — session cookie expired or invalid.")
        return []

    html_text = resp.text

    # Many React apps embed initial state in window.__INITIAL_STATE__ or similar
    for pattern in [
        r"window\.__INITIAL_STATE__\s*=\s*({.+?});",
        r"window\.__handshake_data__\s*=\s*({.+?});",
        r'"job_postings"\s*:\s*(\[.+?\])\s*[,}]',
    ]:
        match = re.search(pattern, html_text, re.DOTALL)
        if match:
            try:
                raw = json.loads(match.group(1))
                postings = (
                    raw.get("job_postings")
                    or raw.get("postings")
                    or (raw if isinstance(raw, list) else [])
                )
                jobs = []
                for p in postings[:want]:
                    pid = str(p.get("id") or "")
                    title = p.get("title") or p.get("position") or ""
                    if pid and title:
                        jobs.append(
                            {
                                "id": f"hs-{pid}",
                                "title": title,
                                "company": (p.get("employer") or {}).get("name") or "Unknown",
                                "location": p.get("location") or "",
                                "date": str(p.get("created_at") or "")[:10],
                                "url": JOB_URL.format(posting_id=pid),
                                "description": p.get("description") or "",
                                "source": SOURCE,
                            }
                        )
                if jobs:
                    return jobs
            except (json.JSONDecodeError, AttributeError):
                pass

    # Last resort: basic HTML card parsing
    soup = BeautifulSoup(html_text, "html.parser")
    cards = soup.find_all(
        "li", attrs={"data-hook": lambda v: v and "job-posting" in str(v)}
    ) or soup.find_all("div", class_=lambda c: c and "posting" in (c or "").lower())

    jobs = []
    for card in cards[:want]:
        pid_match = re.search(r"/postings/(\d+)", str(card))
        pid = pid_match.group(1) if pid_match else None
        title_node = card.find(["h3", "h2", "h4"])
        if not pid or not title_node:
            continue
        jobs.append(
            {
                "id": f"hs-{pid}",
                "title": title_node.get_text(strip=True),
                "company": "Unknown",
                "location": "",
                "date": "",
                "url": JOB_URL.format(posting_id=pid),
                "description": "",
                "source": SOURCE,
            }
        )
    return jobs


def _fetch_description(sess: requests.Session, posting_id_raw: str) -> str:
    """Fetch the full description from the individual posting page."""
    pid = posting_id_raw.removeprefix("hs-")
    try:
        resp = sess.get(JOB_URL.format(posting_id=pid), timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try JSON-LD first (Handshake does embed this)
    import json as _json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = _json.loads(script.string or "")
            if isinstance(data, list):
                data = next((d for d in data if d.get("@type") == "JobPosting"), {})
            if data.get("description"):
                return BeautifulSoup(data["description"], "html.parser").get_text(
                    separator="\n", strip=True
                )
        except Exception:
            continue

    # Fallback: visible description section
    node = (
        soup.find(attrs={"data-hook": "job-description"})
        or soup.find(class_=lambda c: c and "description" in (c or "").lower())
    )
    return node.get_text(separator="\n", strip=True) if node else ""


def scrape(keywords: str, _location: str, want: int) -> list[dict]:
    cookie_str = os.environ.get("HANDSHAKE_SESSION_COOKIE", "").strip()
    if not cookie_str:
        print("  [Handshake] HANDSHAKE_SESSION_COOKIE not set — skipping.")
        return []

    email = os.environ.get("HANDSHAKE_EMAIL", "")
    sess = _session(cookie_str, email)

    print(f"  [Handshake] searching: {keywords}")
    jobs = _api_search(sess, keywords, want)
    if not jobs:
        print("  [Handshake] API returned nothing — trying HTML fallback…")
        jobs = _html_search(sess, keywords, want)

    print(f"  [Handshake] {len(jobs)} posting(s) found.")

    for job in jobs:
        if not job.get("description"):
            _sleep()
            job["description"] = _fetch_description(sess, job["id"])

    return [j for j in jobs if j["description"]]
