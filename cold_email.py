"""
Generates a short cold outreach email to the hiring manager/recruiter
for each job. Keeps it under 150 words — concise emails get responses.
"""

import urllib.parse
from google import genai
from google.genai import types
import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """\
You are writing a cold outreach email for a CS student applying to internships.

Rules:
- 3-4 sentences MAX, under 120 words total.
- Sentence 1: who you are + what role you're applying for.
- Sentence 2: one specific, impressive thing from their projects/experience that matches this company.
- Sentence 3: a clear, low-friction call to action ("Would love to connect" or "Happy to share more").
- Start with: Dear [Hiring Manager Name],
- End with a signature block placeholder.
- NO fluff, NO "I hope this email finds you well", NO generic phrases.
- Plain text only, no markdown.
- NEVER invent facts not in the resume.
"""


def generate(resume_text: str, job: dict) -> str:
    prompt = (
        f"Job: {job['title']} at {job['company']} ({job.get('location', '')})\n\n"
        f"Job Description (first 800 chars):\n{job['description'][:800]}\n\n"
        f"Candidate Resume:\n{resume_text[:2000]}\n\n"
        "Write the cold outreach email (plain text, under 120 words)."
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


def recruiter_search_url(company: str) -> str:
    """Returns a LinkedIn people search URL to find the recruiter at this company."""
    query = urllib.parse.quote(f"{company} university recruiter internship")
    return f"https://www.linkedin.com/search/results/people/?keywords={query}"
