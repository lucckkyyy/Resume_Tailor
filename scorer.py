"""
Scores each job 0-10 for relevance to the candidate before tailoring or applying.

A fast, cheap pass using a short prompt — runs in under a second per job.
Jobs below MIN_SCORE_TO_APPLY are skipped entirely (not tailored, not applied to).
Jobs between MIN_SCORE_TO_APPLY and MIN_SCORE_TO_AUTOAPPLY get a tailored resume
prepared but are NOT auto-applied — you apply manually from the email links.
Jobs at or above MIN_SCORE_TO_AUTOAPPLY get the full auto-apply treatment.

Response format: JSON {"score": <0-10>, "reason": "<one sentence>"}
"""

import json
import re

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """\
You are a brutally honest career advisor helping a computer science student
find relevant co-op and internship positions.

Score the job 0-10 based on fit with the candidate's background.
Return ONLY valid JSON — no preamble, no markdown fences:
{"score": <integer 0-10>, "reason": "<one sentence explaining the score>"}

Scoring guide:
  9-10  Perfect fit: keywords align tightly, no red flags
  7-8   Good fit: mostly aligns, minor gaps
  5-6   Partial: some overlap but significant gaps
  3-4   Weak: mostly irrelevant but something in common
  0-2   No fit: totally different field, too senior, or suspicious listing
"""


def score(resume_text: str, job: dict) -> dict:
    """Return {"score": int, "reason": str}. Falls back to score=5 on error."""
    prompt = (
        f"CANDIDATE BACKGROUND (resume excerpt, first 1500 chars):\n"
        f"{resume_text[:1500]}\n\n"
        f"JOB:\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Source: {job['source']}\n"
        f"Description (first 800 chars):\n{job['description'][:800]}"
    )
    try:
        resp = _client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=120,
            ),
        )
        raw = (resp.text or "").strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"^```[a-z]*|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return {"score": int(data["score"]), "reason": str(data["reason"])}
    except Exception as exc:
        print(f"    [scorer] failed for '{job['title']}': {exc}")
        return {"score": 5, "reason": "Score unavailable (AI error)"}
