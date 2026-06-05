"""
Google API helpers:
  read_resume_text()    — export master Google Doc as plain text
  export_doc_as_pdf()   — export a Google Doc as a PDF file (for resume upload)
  create_resume_doc()   — create a new Google Doc with tailored text
  send_summary_email()  — send the morning email via Gmail SMTP
"""

import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import config

_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _creds() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri=_TOKEN_URI,
        scopes=config.GOOGLE_SCOPES,
    )

def _drive():  return build("drive",  "v3", credentials=_creds(), cache_discovery=False)
def _docs():   return build("docs",   "v1", credentials=_creds(), cache_discovery=False)


def read_resume_text(doc_id: str) -> str:
    data = _drive().files().export(fileId=doc_id, mimeType="text/plain").execute()
    return data.decode("utf-8") if isinstance(data, bytes) else str(data)


def export_doc_as_pdf(doc_id: str) -> str:
    """Export a Google Doc as PDF; returns path to a temporary file."""
    data = _drive().files().export(fileId=doc_id, mimeType="application/pdf").execute()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


def create_resume_doc(title: str, body_text: str) -> str:
    """Create a Google Doc and return its shareable URL."""
    docs  = _docs()
    drive = _drive()

    doc    = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": body_text}}]},
    ).execute()

    if config.OUTPUT_FOLDER_ID:
        drive.files().update(
            fileId=doc_id, addParents=config.OUTPUT_FOLDER_ID, fields="id,parents"
        ).execute()

    if config.SHARE_DOCS_PUBLIC:
        drive.permissions().create(
            fileId=doc_id, body={"type": "anyone", "role": "reader"}, fields="id"
        ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"


def send_summary_email(to_addr: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.GMAIL_ADDRESS
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        s.sendmail(config.GMAIL_ADDRESS, [to_addr], msg.as_string())
