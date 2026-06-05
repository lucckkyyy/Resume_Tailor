"""
Sends (master resume + one job description) to Gemini and gets back a tailored,
ATS-ready plain-text resume. The system instruction forbids inventing anything.
"""

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """\
You are an expert resume writer specializing in ATS (applicant tracking system) optimization.

You will receive a candidate's MASTER RESUME and a single JOB DESCRIPTION.
Rewrite the resume so it is tailored to that specific job.

Hard rules:
- Do NOT invent facts, companies, job titles, dates, degrees, certifications, or metrics.
  Use ONLY information present in the master resume. If something isn't there, omit it.
- You may reorder, rephrase, and re-emphasize real experience to match the job's
  keywords, tone, and requirements.
- Start every bullet with a strong action verb.
- Mirror the job's important keywords where they truthfully apply to the candidate.
- Output ATS-friendly PLAIN TEXT only: no markdown, no tables, no special characters,
  no commentary before or after. Just the finished resume text.
"""


def tailor_resume(resume_text: str, job: dict) -> str:
    prompt = (
        f"JOB TITLE: {job['title']}\n"
        f"COMPANY: {job['company']}\n"
        f"LOCATION: {job['location']}\n\n"
        f"JOB DESCRIPTION:\n{job['description']}\n\n"
        f"MASTER RESUME:\n{resume_text}\n\n"
        "Return the tailored resume as plain text only."
    )

    response = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.4,
        ),
    )
    return (response.text or "").strip()
