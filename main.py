"""
Daily orchestrator.

Full flow per job:
  1. Score relevance (Gemini, fast)              → skip if below MIN_SCORE_TO_PREPARE
  2. Tailor resume (Gemini)                      → create Google Doc
  3. Write cover letter (Gemini)                 → create Google Doc
  4. Export resume as PDF                        → for Easy Apply upload
  5. If LinkedIn + score ≥ MIN_SCORE_TO_AUTOAPPLY + AUTO_APPLY=true
       → attempt LinkedIn Easy Apply (Playwright)
     else → put in "Apply yourself" bucket
  6. Log to Google Sheet tracker
  7. Send summary email with three sections:
       ✅ Auto-applied  |  📋 Ready for you  |  ⏭ Skipped
"""

import datetime
import html
import os
import sys
import traceback

import config
import cold_email as ce
import cover_letter as cl
import github_projects as gh
import google_clients as g
import scorer
import tailor
import tracker
from scrapers import fetch_all

if config.AUTO_APPLY:
    import applier


# ── Colours / badges ────────────────────────────────────────────────────────
SOURCE_COLORS = {"LinkedIn": "#0077B5", "Indeed": "#2164F3", "Handshake": "#E03E2D"}
STATUS_COLORS = {"applied": "#27ae60", "external": "#e67e22",
                 "failed":  "#e74c3c", "skip":     "#95a5a6",
                 "no_auth": "#e74c3c"}

def badge(text, color):
    return (f"<span style='background:{color};color:#fff;padding:2px 8px;"
            f"border-radius:3px;font-size:11px;font-weight:bold'>{html.escape(text)}</span>")

def src_badge(source):
    return badge(source, SOURCE_COLORS.get(source, "#555"))

def score_badge(s):
    color = "#27ae60" if s >= 8 else "#e67e22" if s >= 6 else "#e74c3c"
    return badge(f"{s}/10", color)


# ── Email builder ────────────────────────────────────────────────────────────
_TH = "style='padding:8px;text-align:left;background:#f0f4f8;border-bottom:2px solid #ddd'"
_TD = "style='padding:8px;border-bottom:1px solid #eee'"

def _row(cells):
    return "<tr>" + "".join(f"<td {_TD}>{c}</td>" for c in cells) + "</tr>"

def _table(header_cells, rows):
    head = "<tr>" + "".join(f"<th {_TH}>{c}</th>" for c in header_cells) + "</tr>"
    return (
        "<table cellpadding='0' cellspacing='0' border='0' "
        "style='border-collapse:collapse;font-family:sans-serif;font-size:13px;"
        "width:100%;margin-bottom:24px'>"
        f"{head}{''.join(rows)}"
        "</table>"
    )

def _link(url, text="↗"):
    return f"<a href='{html.escape(url)}' style='color:#0077b5'>{html.escape(text)}</a>"

def build_email(applied, ready, skipped, keywords, today):
    parts = [
        f"<div style='font-family:sans-serif;max-width:900px'>",
        f"<h2 style='color:#1a1a1a'>Daily Job Digest — {html.escape(today)}</h2>",
        f"<p>Search: <b>{html.escape(keywords)}</b> &nbsp;·&nbsp; "
        f"<b>{len(applied)}</b> auto-applied &nbsp;·&nbsp; "
        f"<b>{len(ready)}</b> ready for you &nbsp;·&nbsp; "
        f"<b>{len(skipped)}</b> skipped</p>",
    ]

    if applied:
        parts.append("<h3 style='color:#27ae60'>✅ Auto-Applied</h3>")
        rows = [_row([
            src_badge(j["source"]),
            html.escape(j["company"]),
            html.escape(j["title"]),
            score_badge(j["score"]),
            _link(j["url"], "Job"),
            _link(j["resume_url"], "Resume"),
            _link(j["cover_url"], "Cover letter"),
            _link(j["cold_url"], "Cold email") if j.get("cold_url") else "—",
            _link(j["recruiter_url"], "Find recruiter ↗") if j.get("recruiter_url") else "—",
        ]) for j in applied]
        parts.append(_table(
            ["Source","Company","Role","Score","Job","Resume","Cover Letter","Cold Email","Find Recruiter"], rows
        ))

    if ready:
        parts.append("<h3 style='color:#e67e22'>📋 Ready for You — Click to Apply</h3>")
        rows = [_row([
            src_badge(j["source"]),
            html.escape(j["company"]),
            html.escape(j["title"]),
            score_badge(j["score"]),
            _link(j["url"], "Job"),
            _link(j["resume_url"], "Resume"),
            _link(j["cover_url"], "Cover letter"),
            _link(j["cold_url"], "Cold email") if j.get("cold_url") else "—",
            _link(j["recruiter_url"], "Find recruiter ↗") if j.get("recruiter_url") else "—",
            html.escape(j.get("apply_note", "")),
        ]) for j in ready]
        parts.append(_table(
            ["Source","Company","Role","Score","Job","Resume","Cover Letter","Cold Email","Find Recruiter","Note"], rows
        ))

    if skipped:
        parts.append("<h3 style='color:#95a5a6'>⏭ Skipped — Low Relevance</h3>")
        rows = [_row([
            src_badge(j["source"]),
            html.escape(j["company"]),
            html.escape(j["title"]),
            score_badge(j["score"]),
            html.escape(j.get("reason", "")),
        ]) for j in skipped]
        parts.append(_table(["Source","Company","Role","Score","Reason"], rows))

    if not (applied or ready or skipped):
        parts.append("<p>No fresh listings found in the last 24h. "
                     "Try widening SEARCH_KEYWORDS or SEARCH_LOCATION.</p>")

    parts.append(
        "<p style='color:#999;font-size:11px;margin-top:24px'>"
        "Always review your resume and cover letter before any application. "
        "The AI tailors wording but never invents facts.</p></div>"
    )
    return "".join(parts)


# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    today = datetime.date.today().isoformat()
    print(f"[{today}] Starting | keywords='{config.SEARCH_KEYWORDS}' "
          f"location='{config.SEARCH_LOCATION}' auto_apply={config.AUTO_APPLY}")

    # ── 1. Scrape ──────────────────────────────────────────────────────────
    jobs = fetch_all(config.SEARCH_KEYWORDS, config.SEARCH_LOCATION,
                     config.MAX_JOBS_PER_SOURCE)
    print(f"Total unique jobs: {len(jobs)}")
    if not jobs:
        g.send_summary_email(config.NOTIFY_EMAIL,
                             f"[Resume Tailor] No listings found — {today}",
                             build_email([], [], [], config.SEARCH_KEYWORDS, today))
        return

    # ── 2. Load master resume once ─────────────────────────────────────────
    print("Loading master resume…")
    resume_text = g.read_resume_text(config.RESUME_DOC_ID)

    GH_USERNAME = os.environ.get("GH_USERNAME", "").strip()
    if GH_USERNAME:
        projects_text = gh.fetch_projects(GH_USERNAME)
        if projects_text:
            resume_text = resume_text + "\n\n" + projects_text
            print("  GitHub projects appended to resume context.")

    # ── 3. Setup tracker ────────────────────────────────────────────────────
    sheet_id = tracker.ensure_sheet(config.TRACKER_SHEET_ID or None)

    applied_list, ready_list, skipped_list = [], [], []

    for job in jobs:
        label = f"{job['source']} | {job['company']} — {job['title']}"
        print(f"\n→ {label}")

        # ── Score ──────────────────────────────────────────────────────────
        result = scorer.score(resume_text, job)
        sc, reason = result["score"], result["reason"]
        job["score"] = sc
        print(f"   Score: {sc}/10 — {reason}")

        if sc < config.MIN_SCORE_TO_PREPARE:
            print("   Skipping (below MIN_SCORE_TO_PREPARE).")
            skipped_list.append({**job, "reason": reason})
            tracker.log_application(sheet_id, job, sc, "Skipped",
                                    "", "", reason)
            continue

        # ── Tailor resume ──────────────────────────────────────────────────
        try:
            tailored = tailor.tailor_resume(resume_text, job)
            resume_title = f"ATS Resume - {job['company']} - {job['title']} - {today}"
            resume_url = g.create_resume_doc(resume_title, tailored)
            print(f"   Resume doc: {resume_url}")
        except Exception as exc:
            print(f"   ! Resume tailor failed: {exc}")
            continue

        # ── Cover letter ───────────────────────────────────────────────────
        try:
            cl_text = cl.generate(resume_text, job)
            cl_title = f"Cover Letter - {job['company']} - {job['title']} - {today}"
            cover_url = g.create_resume_doc(cl_title, cl_text)
            print(f"   Cover letter: {cover_url}")
        except Exception as exc:
            print(f"   ! Cover letter failed: {exc}")
            cover_url = ""

        # ── Cold email ─────────────────────────────────────────────────────
        try:
            cold_text  = ce.generate(resume_text, job)
            recruiter_url = ce.recruiter_search_url(job["company"])
            cold_title = f"Cold Email - {job['company']} - {job['title']} - {today}"
            cold_url   = g.create_resume_doc(cold_title, cold_text)
            print(f"   Cold email: {cold_url}")
        except Exception as exc:
            print(f"   ! Cold email failed: {exc}")
            cold_url      = ""
            recruiter_url = ce.recruiter_search_url(job["company"])

        # ── Auto-apply decision ────────────────────────────────────────────
        apply_status = "skip"
        apply_note   = ""

        should_autoapply = (
            config.AUTO_APPLY
            and sc >= config.MIN_SCORE_TO_AUTOAPPLY
            and "linkedin.com" in job.get("url", "")
        )

        if should_autoapply:
            print("   Attempting LinkedIn Easy Apply…")
            try:
                pdf_path = g.export_doc_as_pdf(
                    resume_url.split("/d/")[1].split("/")[0]
                )
                result_apply = applier.apply(job, pdf_path)
                apply_status = result_apply["status"]
                apply_note   = result_apply["message"]
                print(f"   Apply result: {apply_status} — {apply_note}")

                # Instant confirmation email for each successful application
                if apply_status == "applied":
                    try:
                        confirm_html = (
                            "<div style='font-family:sans-serif;max-width:600px'>"
                            "<h2 style='color:#27ae60'>&#x2705; Application Submitted!</h2>"
                            "<p>Your resume was just automatically submitted for:</p>"
                            f"<p><b>Role:</b> {html.escape(job['title'])}<br>"
                            f"<b>Company:</b> {html.escape(job['company'])}<br>"
                            f"<b>Source:</b> {html.escape(job['source'])}<br>"
                            f"<b>Match Score:</b> {sc}/10</p>"
                            f"<p><a href='{html.escape(job['url'])}'>View Job &#x2197;</a> &nbsp;&nbsp; "
                            f"<a href='{html.escape(resume_url)}'>Your Tailored Resume &#x2197;</a></p>"
                            f"<p style='color:#888;font-size:12px'>Applied via LinkedIn Easy Apply on "
                            f"{datetime.date.today().isoformat()}. "
                            "Follow up within 48 hours for best results.</p>"
                            "</div>"
                        )
                        g.send_summary_email(
                            config.NOTIFY_EMAIL,
                            f"Applied: {job['title']} at {job['company']}",
                            confirm_html,
                        )
                        print("   Confirmation email sent.")
                    except Exception as mail_exc:
                        print(f"   ! Confirmation email failed: {mail_exc}")

                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
            except Exception as exc:
                apply_status = "failed"
                apply_note   = str(exc)
                print(f"   ! Apply exception: {exc}")

        # ── Bucket ─────────────────────────────────────────────────────────
        entry = {**job, "score": sc, "resume_url": resume_url,
                 "cover_url": cover_url, "cold_url": cold_url,
                 "recruiter_url": recruiter_url, "apply_note": apply_note}

        if apply_status == "applied":
            applied_list.append(entry)
            tracker.log_application(sheet_id, job, sc, "Applied ✅",
                                    resume_url, cover_url, reason)
        else:
            note_map = {
                "external":  "External ATS — apply via Job link",
                "no_auth":   "No LinkedIn auth state configured",
                "failed":    f"Auto-apply failed: {apply_note}",
                "skip":      "Score below auto-apply threshold" if sc < config.MIN_SCORE_TO_AUTOAPPLY
                             else "AUTO_APPLY is off",
            }
            entry["apply_note"] = note_map.get(apply_status, apply_note)
            ready_list.append(entry)
            tracker.log_application(sheet_id, job, sc,
                                    f"Ready ({apply_status})",
                                    resume_url, cover_url, reason)

    # ── 4. Send email ──────────────────────────────────────────────────────
    total = len(applied_list) + len(ready_list)
    subject = (
        f"[Resume Tailor] {len(applied_list)} applied, "
        f"{len(ready_list)} ready for you — {today}"
    )
    html_body = build_email(applied_list, ready_list, skipped_list,
                            config.SEARCH_KEYWORDS, today)
    g.send_summary_email(config.NOTIFY_EMAIL, subject, html_body)
    print(f"\nEmail sent. Applied={len(applied_list)} Ready={len(ready_list)} "
          f"Skipped={len(skipped_list)}")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
