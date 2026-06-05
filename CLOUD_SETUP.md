# Cloud Setup Guide — Start Today, No Installs Needed

Everything in this guide runs in your browser. Estimated time: 45-55 minutes.

Two steps from the regular README normally require running Python locally.
This guide replaces both with browser-only alternatives:

| Original step | Cloud replacement |
|---------------|-------------------|
| `python get_token.py` | Google OAuth Playground (browser) |
| `python get_linkedin_state.py` | Copy li_at cookie from DevTools (browser) |

---

## Keep a notes doc open and paste each value as you collect it:

```
GEMINI_API_KEY            =
GOOGLE_CLIENT_ID          =
GOOGLE_CLIENT_SECRET      =
GOOGLE_REFRESH_TOKEN      =
GMAIL_ADDRESS             =
GMAIL_APP_PASSWORD        =
RESUME_DOC_ID             =
LINKEDIN_COOKIE           =
SEARCH_KEYWORDS           =
SEARCH_LOCATION           =
APPLICANT_FIRST_NAME      =
APPLICANT_LAST_NAME       =
APPLICANT_PHONE           =
APPLICANT_LINKEDIN_URL    =
APPLICANT_GPA             =
APPLICANT_GRADUATION_DATE =
APPLICANT_DEGREE          =
APPLICANT_UNIVERSITY      =
APPLICANT_AUTHORIZED_US   = yes
APPLICANT_NEEDS_SPONSORSHIP = no
```

---

## Step 1 — Gemini API key (3 min)

1. Open https://aistudio.google.com and sign in with your Google account.
2. Click "Get API key" (top-left) then "Create API key" — select or create a project.
3. Copy the key.

Save as: GEMINI_API_KEY

---

## Step 2 — Google Cloud: OAuth client (12 min)

### 2a. Create a project and enable APIs

1. Open https://console.cloud.google.com (same Google account).
2. Click the project selector at the top > "New Project" > name it "resume-tailor" > Create.
3. Make sure the new project is selected.
4. Go to APIs & Services > Library.
5. Search for and Enable each of these one at a time:
   - Google Docs API
   - Google Drive API
   - Google Sheets API

### 2b. OAuth consent screen

1. APIs & Services > OAuth consent screen.
2. Choose External > Create.
3. Fill in App name ("Resume Tailor"), your email for support and contact. Click Save and Continue
   through the Scopes and Test Users pages without changing anything.
4. Back on the summary — click "Publish App" > Confirm.

   IMPORTANT: "In production" prevents your refresh token from expiring after 7 days.
   You will see an "unverified app" warning when you authorize — that is fine for
   personal use. Just click Advanced > Go to resume-tailor (unsafe).

### 2c. Create OAuth credentials

1. APIs & Services > Credentials > Create Credentials > OAuth client ID.
2. Application type: Desktop app > name it anything > Create.
3. Copy the Client ID and Client secret from the dialog.

Save as: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

---

## Step 3 — Get the Google refresh token via OAuth Playground (8 min)

This replaces running get_token.py. No Python needed.

1. Open https://developers.google.com/oauthplayground in a new tab.

2. Click the gear icon (top-right) > check "Use your own OAuth credentials"
   > paste your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET > close the settings.

3. In the left panel, find "Input your own scopes" at the top.
   Paste this entire line and click "Authorize APIs":

   https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets

4. Sign in to Google. You will see an "unverified app" warning.
   Click "Advanced" > "Go to resume-tailor (unsafe)" > Allow.

5. Back on the Playground, click "Exchange authorization code for tokens".

6. In the response panel on the right, find "refresh_token" — it starts with "1//".
   Copy the entire value inside the quotes.

Save as: GOOGLE_REFRESH_TOKEN

---

## Step 4 — Gmail App Password (4 min)

1. First confirm 2-Step Verification is ON for your Google account:
   https://myaccount.google.com/security
   If it is off, turn it on (takes 2 minutes). App Passwords require it.

2. Go to https://myaccount.google.com/apppasswords

3. Under "App name" type "Resume Tailor" > Create.

4. Copy the 16-character code that appears. Remove the spaces (e.g., abcdefghijklmnop).

Save as: GMAIL_ADDRESS (your Gmail) and GMAIL_APP_PASSWORD (the 16-char code)

---

## Step 5 — Resume Google Doc ID (1 min)

1. Open your resume in Google Docs.
2. The URL looks like:
   docs.google.com/document/d/  THIS-LONG-STRING  /edit
3. Copy that long string in the middle.

Save as: RESUME_DOC_ID

---

## Step 6 — LinkedIn cookie for auto-apply (3 min)

This replaces running get_linkedin_state.py. No Python needed.

1. Go to https://www.linkedin.com — you are already logged in.
2. Press F12 to open DevTools.
3. Click the "Application" tab (Chrome) or "Storage" tab (Firefox).
4. In the left panel: Cookies > https://www.linkedin.com
5. Find the cookie named li_at and click on it.
6. Copy the entire Value field (it is 100+ characters long).

Save as: LINKEDIN_COOKIE

Note: This cookie lasts about 60 days. When Easy Apply stops working,
come back here and copy a fresh li_at value.

---

## Step 7 — Applicant profile (3 min)

Fill in the rest of your notes from the template at the top:

SEARCH_KEYWORDS       - e.g. "software engineering internship OR co-op"
SEARCH_LOCATION       - e.g. "United States"
APPLICANT_FIRST_NAME  - Your first name
APPLICANT_LAST_NAME   - Your last name
APPLICANT_PHONE       - e.g. +15551234567
APPLICANT_LINKEDIN_URL - Your full LinkedIn profile URL
APPLICANT_GPA         - e.g. 3.7
APPLICANT_GRADUATION_DATE - e.g. May 2026
APPLICANT_DEGREE      - e.g. Bachelor of Science in Computer Science
APPLICANT_UNIVERSITY  - Your university name
APPLICANT_AUTHORIZED_US - yes or no
APPLICANT_NEEDS_SPONSORSHIP - yes or no

---

## Step 8 — Create the GitHub repo and upload code (10 min)

### 8a. Create a GitHub account (if needed)
Go to https://github.com > Sign up. Use your personal email.

### 8b. Create a new repository
Click "+" (top-right) > "New repository"
- Name: resume-tailor
- Visibility: Public (unlimited free Actions minutes). Private gives 2,000 min/month which is enough.
- Click "Create repository"

### 8c. Upload the files
On your office computer, extract the zip file you downloaded
(right-click > Extract All on Windows, double-click on Mac).

You get a folder called job-resume-tailor with all the files inside.

On GitHub, in your new empty repo:
1. Click "Add file" > "Upload files"
2. Open the job-resume-tailor folder and select ALL files and folders inside it
3. Drag them into the GitHub upload box
4. If GitHub rejects folders, upload the root files first, then for each subfolder:
   - Click "Add file" > "Create new file"
   - Type the path like: scrapers/__init__.py
   - GitHub creates the folder automatically
   - Paste the file contents
   - Commit
   Subfolders needed: scrapers/ (4 files) and .github/workflows/ (1 file)
5. Scroll down > "Commit changes" > "Commit directly to main" > Commit

---

## Step 9 — Add GitHub Secrets (8 min)

In your repo: Settings > Secrets and variables > Actions > "New repository secret"

Add each secret (name exactly as shown, value from your notes):

REQUIRED:
  GEMINI_API_KEY
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  GMAIL_ADDRESS
  GMAIL_APP_PASSWORD
  RESUME_DOC_ID
  SEARCH_KEYWORDS
  SEARCH_LOCATION

AUTO-APPLY:
  LINKEDIN_COOKIE          (the li_at value from Step 6)
  AUTO_APPLY               (type: false to start — change to true when ready)
  MIN_SCORE_TO_PREPARE     (type: 6)
  MIN_SCORE_TO_AUTOAPPLY   (type: 8)

APPLICANT PROFILE:
  APPLICANT_FIRST_NAME
  APPLICANT_LAST_NAME
  APPLICANT_PHONE
  APPLICANT_LINKEDIN_URL
  APPLICANT_GPA
  APPLICANT_GRADUATION_DATE
  APPLICANT_DEGREE
  APPLICANT_UNIVERSITY
  APPLICANT_AUTHORIZED_US
  APPLICANT_NEEDS_SPONSORSHIP

OPTIONAL (skip for now):
  HANDSHAKE_SESSION_COOKIE   (see main README — get this from Handshake DevTools)
  MAX_JOBS_PER_SOURCE        (default: 5)
  NOTIFY_EMAIL               (defaults to your GMAIL_ADDRESS)

---

## Step 10 — First run (2 min)

1. In your repo, click the "Actions" tab.
2. Click "Daily Resume Tailor + Auto-Apply" in the left sidebar.
3. Click "Run workflow" > "Run workflow" (green button).

First run takes 4-6 minutes — most of that is Playwright downloading Chromium.

Watch the logs. When it finishes, check your inbox.

The run log also prints a Google Sheet ID — copy it and add it as TRACKER_SHEET_ID
Secret so your application history persists across daily runs.

---

## Step 11 — Enable auto-apply

After the first run looks good:

1. Settings > Secrets > Actions > find AUTO_APPLY > Update > change to: true
2. Run workflow again manually to test.
3. Check your email — the "Auto-Applied" section should now appear.

The daily cron runs weekdays at 12:00 UTC (8 AM Eastern / 7 AM Central).
To change the time: edit .github/workflows/daily-resume-tailor.yml, find the cron: line.
Use crontab.guru to convert your timezone to UTC.

---

## Troubleshooting

Symptom                     | Fix
"Missing required env var"  | A Secret is missing or misspelled — recheck Step 9
No jobs found               | Broaden SEARCH_KEYWORDS, or LinkedIn throttled the scraper (retry next day)
Refresh token error         | Redo Step 3; confirm app is "In production" from Step 2b
Easy Apply keeps failing    | Check Actions log; set AUTO_APPLY=false temporarily, LinkedIn may have updated their UI
li_at stopped working       | LinkedIn session expired — repeat Step 6
