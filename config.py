"""
Central config — read from environment variables only. Nothing secret here.
"""
import os

def _require(name):
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v

# ── Gemini ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = _require("GEMINI_API_KEY")
GEMINI_MODEL    = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

# ── Google OAuth (Drive + Docs + Sheets) ───────────────────────────────────
GOOGLE_CLIENT_ID     = _require("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _require("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = _require("GOOGLE_REFRESH_TOKEN")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# ── Email (Gmail SMTP + App Password) ──────────────────────────────────────
GMAIL_ADDRESS    = _require("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _require("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL     = os.environ.get("NOTIFY_EMAIL", GMAIL_ADDRESS).strip()

# ── Your resume ────────────────────────────────────────────────────────────
RESUME_DOC_ID    = _require("RESUME_DOC_ID")
OUTPUT_FOLDER_ID = os.environ.get("OUTPUT_FOLDER_ID", "").strip()

# ── Job search ─────────────────────────────────────────────────────────────
SEARCH_KEYWORDS        = os.environ.get("SEARCH_KEYWORDS",
                           "software engineering internship OR co-op").strip()
SEARCH_LOCATION        = os.environ.get("SEARCH_LOCATION", "United States").strip()
MAX_JOBS_PER_SOURCE    = int(os.environ.get("MAX_JOBS_PER_SOURCE", "5"))

# ── Job filtering ──────────────────────────────────────────────────────────
# Jobs scored below MIN_SCORE_TO_PREPARE are skipped entirely (no resume, no apply).
MIN_SCORE_TO_PREPARE   = int(os.environ.get("MIN_SCORE_TO_PREPARE",   "6"))
# Jobs scored AT OR ABOVE MIN_SCORE_TO_AUTOAPPLY get LinkedIn Easy Apply attempted.
MIN_SCORE_TO_AUTOAPPLY = int(os.environ.get("MIN_SCORE_TO_AUTOAPPLY", "8"))

# ── Auto-apply master switch ───────────────────────────────────────────────
# Set to "true" to enable LinkedIn Easy Apply automation.
# Default false — you can stage: run with false first to review, then enable.
AUTO_APPLY = os.environ.get("AUTO_APPLY", "false").lower() == "true"

# ── Applicant profile (used to fill screening questions) ──────────────────
# These are read directly in applier.py from env — listed here for reference.
# APPLICANT_FIRST_NAME, APPLICANT_LAST_NAME, APPLICANT_PHONE
# APPLICANT_LINKEDIN_URL, APPLICANT_GPA, APPLICANT_GRADUATION_DATE
# APPLICANT_DEGREE, APPLICANT_UNIVERSITY
# APPLICANT_AUTHORIZED_US (yes/no), APPLICANT_NEEDS_SPONSORSHIP (yes/no)

# ── LinkedIn auto-apply auth (set by get_linkedin_state.py) ───────────────
# LINKEDIN_AUTH_STATE — base64 Playwright storage state (set in GitHub Secrets)

# ── Application tracker (Google Sheet) ───────────────────────────────────
# Optional. First run without it creates a new sheet and prints the ID.
# Then add TRACKER_SHEET_ID as a Secret to persist across runs.
TRACKER_SHEET_ID = os.environ.get("TRACKER_SHEET_ID", "").strip()

# ── Misc ───────────────────────────────────────────────────────────────────
SHARE_DOCS_PUBLIC = os.environ.get("SHARE_DOCS_PUBLIC", "true").lower() == "true"
