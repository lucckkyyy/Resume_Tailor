# Daily Resume Tailor + Auto-Apply — LinkedIn / Indeed / Handshake

Every morning GitHub Actions wakes up and runs this full pipeline:

```
Scrape fresh internship/co-op listings (LinkedIn + Indeed + Handshake)
        ↓
Score each job 0–10 for relevance  →  skip if below threshold
        ↓
Tailor resume  +  write cover letter  →  create two Google Docs per job
        ↓
LinkedIn Easy Apply jobs (score ≥ 8, AUTO_APPLY=true)  →  auto-apply via Playwright
Other jobs  →  "Apply yourself" bucket in email
        ↓
Log everything to a Google Sheet tracker
        ↓
Send you a three-section email:
  ✅ Auto-Applied  |  📋 Ready for You  |  ⏭ Skipped (low score)
```

## Cost

| Piece | Cost |
|-------|------|
| GitHub Actions (scrape + AI + Playwright) | **Free** — unlimited on public repos, 2,000 min/mo on private |
| Gemini 2.5 Flash API | **Free tier** — 250 req/day; you need ~30 |
| Google Drive / Docs / Sheets / Gmail | **Free** |
| LinkedIn / Indeed / Handshake scraping | **Free** (public endpoints) |
| **Total** | **$0/month** |

> **About your $5/month budget:** you genuinely don't need it for this to run.
> If you want to use it, the highest-ROI option is a **Railway.app $5 plan**
> to run this every 4–6 hours during peak recruiting season (fall co-op listings
> fill within hours). Second option: Gemini paid tier ($0.075/M tokens for Flash —
> at your usage it'd cost ~$0.30/month, and you get 750 RPM vs 15 RPM free).

---

## Setup (one-time, ~45 minutes)

### Step 1 — Gemini API key
**aistudio.google.com → Get API key** → no credit card → save as `GEMINI_API_KEY`.

### Step 2 — Master resume Doc ID
Open your Google Doc resume → copy the long ID from the URL → save as `RESUME_DOC_ID`.

### Step 3 — Google OAuth (Drive + Docs + Sheets)
1. **console.cloud.google.com** → new project → enable:
   - Google Docs API · Google Drive API · Google Sheets API
2. **OAuth consent screen** → External → add your email as Test user.
   ⚠️ Set publishing status to **"In production"** or your refresh token expires in 7 days.
3. **Credentials → Create → OAuth client ID → Desktop app** → download JSON as `client_secret.json`.
4. Run locally:
   ```bash
   pip install -r requirements.txt
   python get_token.py
   ```
   Copy the three printed values: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.

### Step 4 — Gmail App Password
**myaccount.google.com/apppasswords** → create → save 16-char code as `GMAIL_APP_PASSWORD`.
Save your address as `GMAIL_ADDRESS`.

### Step 5 — Handshake session cookie (optional)
1. Log into **app.joinhandshake.com** in Chrome.
2. DevTools (F12) → Application → Cookies → joinhandshake.com.
3. Copy `_handshake_session` value (+ `remember_user_token` if present).
4. Build: `_handshake_session=VALUE; remember_user_token=VALUE` → save as `HANDSHAKE_SESSION_COOKIE`.
5. Save your .edu address as `HANDSHAKE_EMAIL`.
> Renew cookies every ~30 days when Handshake results go empty.

### Step 6 — LinkedIn auth state (required for auto-apply)
```bash
playwright install chromium
python get_linkedin_state.py
```
A browser opens → log in manually → press Enter → copy the printed base64 string
→ save as `LINKEDIN_AUTH_STATE`. Re-run every ~60 days.

### Step 7 — GitHub repo + secrets
1. Push all files to a GitHub repo (public = unlimited Actions minutes).
2. **Settings → Secrets and variables → Actions → New repository secret**:

**Required secrets:**

| Secret | Where to get it |
|--------|----------------|
| `GEMINI_API_KEY` | Step 1 |
| `GOOGLE_CLIENT_ID` | Step 3 |
| `GOOGLE_CLIENT_SECRET` | Step 3 |
| `GOOGLE_REFRESH_TOKEN` | Step 3 |
| `GMAIL_ADDRESS` | Your Gmail |
| `GMAIL_APP_PASSWORD` | Step 4 |
| `RESUME_DOC_ID` | Step 2 |
| `SEARCH_KEYWORDS` | e.g. `software engineering internship OR co-op` |
| `SEARCH_LOCATION` | e.g. `United States` |

**Applicant profile (for screening question auto-fill):**

| Secret | Example |
|--------|---------|
| `APPLICANT_FIRST_NAME` | `Alex` |
| `APPLICANT_LAST_NAME` | `Smith` |
| `APPLICANT_PHONE` | `+15551234567` |
| `APPLICANT_LINKEDIN_URL` | `https://linkedin.com/in/alexsmith` |
| `APPLICANT_GPA` | `3.7` |
| `APPLICANT_GRADUATION_DATE` | `May 2026` |
| `APPLICANT_DEGREE` | `Bachelor of Science in Computer Science` |
| `APPLICANT_UNIVERSITY` | `University of Michigan` |
| `APPLICANT_AUTHORIZED_US` | `yes` |
| `APPLICANT_NEEDS_SPONSORSHIP` | `no` |

**Optional secrets:**

| Secret | Default | Notes |
|--------|---------|-------|
| `AUTO_APPLY` | `false` | Set `true` to enable LinkedIn Easy Apply |
| `LINKEDIN_AUTH_STATE` | — | Step 6. Required if AUTO_APPLY=true |
| `MIN_SCORE_TO_PREPARE` | `6` | Below this: skipped entirely |
| `MIN_SCORE_TO_AUTOAPPLY` | `8` | At/above this: auto-applied (if AUTO_APPLY=true) |
| `MAX_JOBS_PER_SOURCE` | `5` | Per platform. 5×3 = up to 15 jobs/morning |
| `HANDSHAKE_SESSION_COOKIE` | — | Step 5 |
| `HANDSHAKE_EMAIL` | — | Your .edu address |
| `TRACKER_SHEET_ID` | — | Auto-created on first run; add the printed ID |
| `NOTIFY_EMAIL` | Your Gmail | Who receives the summary |
| `OUTPUT_FOLDER_ID` | Drive root | Drive folder for generated docs |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Or `gemini-2.5-flash-lite` for more quota |

### Step 8 — Staged rollout (recommended)
1. First run: leave `AUTO_APPLY=false`. Verify the email looks right, score thresholds make sense.
2. Add `LINKEDIN_AUTH_STATE` (Step 6). Run again with `AUTO_APPLY=false` — verify it finds Easy Apply buttons.
3. Set `AUTO_APPLY=true`. Start applying!

The **Actions tab → Daily Resume Tailor → Run workflow** button lets you trigger it anytime.
The cron runs weekdays at 12:00 UTC by default — edit the yml to match your timezone.

---

## How the scoring works

Every job gets an AI score 0–10 before any resume tailoring happens:

| Score | Action |
|-------|--------|
| 0–5 | **Skipped** — no resume created, no notification clutter |
| 6–7 | **Resume + cover letter created**, put in "Apply yourself" bucket |
| 8–10 | **Resume + cover letter + auto-apply** (if LinkedIn Easy Apply + AUTO_APPLY=true) |

You control the thresholds via `MIN_SCORE_TO_PREPARE` and `MIN_SCORE_TO_AUTOAPPLY`.

---

## What auto-apply can and can't do

| ✅ Works | ⚠️ Best-effort | ❌ Not automated |
|---------|---------------|-----------------|
| LinkedIn "Easy Apply" (simple forms) | Screening questions (AI-answered) | External ATS (Greenhouse, Workday, Taleo) |
| Resume PDF upload | Multi-select / complex forms | Indeed apply |
| Contact info auto-fill | | Handshake apply |

External ATS jobs (the majority of large-company internship postings) get the
"📋 Ready for You" treatment — everything's prepared, you just click the link.

---

## Honest caveats

- **LinkedIn may detect and restrict your account.** Bots violate their ToS. The script
  mimics human timing but the risk is real. Keep `MAX_JOBS_PER_SOURCE` ≤ 5 and run once daily.
- **Screening questions are answered by AI from your profile.** Always spot-check the
  Applied section in your email — occasionally the AI picks a wrong radio button.
- **Easy Apply form structure changes.** If applications fail, check the Actions log.
  The Playwright selectors in `applier.py` may need updating when LinkedIn redesigns their UI.
- **Handshake cookies expire** (~30 days). Renew when Handshake results go silent.
- **Never commit** `client_secret.json` or `linkedin_state.json` (both are in `.gitignore`).
