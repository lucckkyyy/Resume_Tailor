"""
Logs every processed job to a Google Sheet for easy tracking.

First run: creates the sheet and prints its ID.
            Add that ID as the TRACKER_SHEET_ID GitHub Secret.
Subsequent runs: appends a row per job.

Sheet columns:
  Date | Company | Role | Source | Score | Status | Job URL | Resume URL | Cover Letter URL | Reason
"""

import datetime
import os

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

_TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

HEADERS = [
    "Date", "Company", "Role", "Source", "Score",
    "Status", "Job URL", "Resume Doc", "Cover Letter Doc", "AI Reason",
]

SHEET_TITLE = "Job Application Tracker — Resume Tailor"


def _creds():
    import config
    return Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri=_TOKEN_URI,
        scopes=SCOPES,
    )


def _service():
    return build("sheets", "v4", credentials=_creds(), cache_discovery=False)


def ensure_sheet(sheet_id: str | None) -> str:
    """Return existing sheet_id or create a new sheet and return its ID."""
    svc = _service()
    if sheet_id:
        return sheet_id

    body = {"properties": {"title": SHEET_TITLE}}
    result = svc.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    new_id = result["spreadsheetId"]

    # Write header row
    svc.spreadsheets().values().update(
        spreadsheetId=new_id,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    print(f"\n  [tracker] New sheet created!")
    print(f"  [tracker] Add this as GitHub Secret TRACKER_SHEET_ID: {new_id}")
    print(f"  [tracker] View at: https://docs.google.com/spreadsheets/d/{new_id}/edit\n")
    return new_id


def log_application(
    sheet_id: str,
    job: dict,
    score: int,
    status: str,
    resume_url: str,
    cover_letter_url: str,
    reason: str,
) -> None:
    today = datetime.date.today().isoformat()
    row = [
        today,
        job.get("company", ""),
        job.get("title", ""),
        job.get("source", ""),
        score,
        status,
        job.get("url", ""),
        resume_url,
        cover_letter_url,
        reason,
    ]
    try:
        _service().spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sheet1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    except Exception as exc:
        print(f"    [tracker] Sheet append failed: {exc}")
