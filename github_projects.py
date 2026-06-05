"""
Fetches your public GitHub repositories and formats them as a projects
supplement that gets appended to your resume text before AI tailoring.

Gemini then sees BOTH your resume AND your actual GitHub projects, so it
can highlight relevant work for each specific job.

Setup: add GITHUB_USERNAME as a GitHub Actions Secret.
       Optionally add GITHUB_TOKEN (a personal access token) to raise the
       rate limit from 60 to 5,000 req/hour — not needed for daily runs.

Uses the public GitHub API — completely free, no auth required for public repos.
"""

import base64
import os
import re
import time

import requests

API_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _readme_intro(owner: str, repo: str, max_chars: int = 400) -> str:
    """Fetch the first meaningful paragraph of a repo's README."""
    try:
        resp = requests.get(
            f"{API_BASE}/repos/{owner}/{repo}/readme",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return ""
        content = base64.b64decode(resp.json()["content"]).decode("utf-8", errors="ignore")
        # Strip markdown headers, badges, images, links
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)   # images
        content = re.sub(r"\[.*?\]\(.*?\)", "", content)    # links
        content = re.sub(r"#+\s*", "", content)              # headers
        content = re.sub(r"`{1,3}.*?`{1,3}", "", content, flags=re.DOTALL)  # code
        content = re.sub(r"\*+|_+", "", content)             # bold/italic
        # Take first non-empty paragraph
        for para in content.split("\n\n"):
            clean = para.strip()
            if len(clean) > 40:   # skip one-liners
                return clean[:max_chars]
    except Exception:
        pass
    return ""


def fetch_projects(username: str, max_repos: int = 12) -> str:
    """
    Return a formatted string of GitHub projects to append to the resume.
    Returns empty string if username not set or API fails.
    """
    if not username:
        return ""

    try:
        resp = requests.get(
            f"{API_BASE}/users/{username}/repos",
            headers=_headers(),
            params={
                "sort": "updated",      # most recently active first
                "per_page": str(max_repos),
                "type": "owner",        # only repos you own (not forks)
            },
            timeout=15,
        )
        resp.raise_for_status()
        repos = resp.json()
    except Exception as exc:
        print(f"  [GitHub] Failed to fetch repos: {exc}")
        return ""

    if not repos:
        return ""

    # Filter out forked repos and very small ones (likely homework/test repos)
    repos = [r for r in repos if not r.get("fork")]

    lines = [
        "=" * 60,
        "GITHUB PROJECTS (additional context for resume tailoring)",
        f"github.com/{username}",
        "=" * 60,
        "",
    ]

    for repo in repos[:max_repos]:
        name        = repo.get("name", "")
        description = repo.get("description") or ""
        language    = repo.get("language") or ""
        stars       = repo.get("stargazers_count", 0)
        url         = repo.get("html_url", "")
        topics      = ", ".join(repo.get("topics", []))
        updated     = (repo.get("updated_at") or "")[:10]

        # Fetch README intro if no description
        readme_text = ""
        if not description:
            readme_text = _readme_intro(username, name)
            time.sleep(0.3)   # be polite to the API

        lines.append(f"Project: {name}")
        lines.append(f"URL: {url}")
        if language:
            lines.append(f"Language: {language}")
        if topics:
            lines.append(f"Topics: {topics}")
        if stars:
            lines.append(f"Stars: {stars}")
        if updated:
            lines.append(f"Last updated: {updated}")
        if description:
            lines.append(f"Description: {description}")
        if readme_text:
            lines.append(f"Details: {readme_text}")
        lines.append("")   # blank line between projects

    print(f"  [GitHub] Loaded {len(repos)} repos for @{username}")
    return "\n".join(lines)
