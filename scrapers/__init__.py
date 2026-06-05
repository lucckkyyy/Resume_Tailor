"""
Runs all three scrapers, merges results, deduplicates by (company, title).
Returns up to MAX_JOBS_PER_SOURCE jobs per source.
"""
import re
from typing import Callable
from . import linkedin, indeed, handshake


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def fetch_all(keywords: str, location: str, max_per_source: int) -> list[dict]:
    sources: list[tuple[str, Callable]] = [
        ("LinkedIn",  linkedin.scrape),
        ("Indeed",    indeed.scrape),
        ("Handshake", handshake.scrape),
    ]
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for name, fn in sources:
        try:
            jobs = fn(keywords, location, max_per_source)
        except Exception as exc:
            print(f"  [{name}] scraper raised: {exc}")
            jobs = []
        added = 0
        for job in jobs:
            key = (_normalize(job.get("company", "")),
                   _normalize(job.get("title", "")))
            if key in seen:
                continue
            seen.add(key)
            merged.append(job)
            added += 1
        print(f"  [{name}] {added} unique new job(s) added.")
    return merged
