"""
Generates a concise, personalized cover letter for one job.
Reads from the master resume — never invents facts.
Output: plain text, 3 tight paragraphs (~200 words), ready to paste.
"""

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """\
You are a career coach writing cover letters for a computer science student
applying to co-op and internship roles.

Rules:
- 3 paragraphs, ~200 words total — no fluff, no filler phrases.
- Paragraph 1: Why this specific company and role excite the candidate.
- Paragraph 2: 1–2 concrete examples from the resume that directly match the JD.
- Paragraph 3: Brief forward-looking closing, availability/start date if known.
- NEVER invent facts, dates, companies, projects, GPA, or skills not in the resume.
- Plain text only — no markdown, no letterhead, no "Dear Hiring Manager" header
  (the applicant will add that). Just the three paragraphs.
"""


def generate(resume_text: str, job: dict) -> str:
    prompt = (
        f"JOB: {job['title']} at {job['company']} ({job.get('location', '')})\n\n"
        f"JOB DESCRIPTION:\n{job['description'][:1500]}\n\n"
        f"CANDIDATE RESUME:\n{resume_text}\n\n"
        "Write the cover letter body (3 paragraphs, plain text only)."
    )
    resp = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.5,
        ),
    )
    return (resp.text or "").strip()
