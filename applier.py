"""
LinkedIn Easy Apply automation using Playwright.

Supports TWO auth methods (use whichever fits your setup):

  A) LINKEDIN_COOKIE  (recommended for cloud/office setup — no local script needed)
     ─ Open LinkedIn in your browser → DevTools (F12) → Application → Cookies
       → linkedin.com → copy the VALUE of the `li_at` cookie
     ─ Store it as the GitHub Secret LINKEDIN_COOKIE

  B) LINKEDIN_AUTH_STATE  (full Playwright storage state — run get_linkedin_state.py locally)
     ─ Only needed if the li_at cookie alone isn't enough to stay logged in

Priority: LINKEDIN_AUTH_STATE > LINKEDIN_COOKIE
If neither is set, returns status "no_auth" and the job goes to "Apply yourself".
"""

import base64
import json
import os
import random
import re
import tempfile
import time

from playwright.sync_api import Page, sync_playwright

import config

_PROFILE = {
    "firstName":         os.environ.get("APPLICANT_FIRST_NAME", ""),
    "lastName":          os.environ.get("APPLICANT_LAST_NAME", ""),
    "email":             config.GMAIL_ADDRESS,
    "phone":             os.environ.get("APPLICANT_PHONE", ""),
    "linkedin":          os.environ.get("APPLICANT_LINKEDIN_URL", ""),
    "gpa":               os.environ.get("APPLICANT_GPA", ""),
    "graduation":        os.environ.get("APPLICANT_GRADUATION_DATE", ""),
    "degree":            os.environ.get("APPLICANT_DEGREE", ""),
    "university":        os.environ.get("APPLICANT_UNIVERSITY", ""),
    "authorized_us":     os.environ.get("APPLICANT_AUTHORIZED_US", "yes"),
    "needs_sponsorship": os.environ.get("APPLICANT_NEEDS_SPONSORSHIP", "no"),
}

from google import genai
from google.genai import types as gtypes
_gemini = genai.Client(api_key=config.GEMINI_API_KEY)

_SCREENING_SYSTEM = """\
You are filling in a job application form on behalf of a student.
Use ONLY the candidate profile to answer. Return ONLY the answer — no explanation.
If yes/no: return 'yes' or 'no'. If a number: return just the number.
Never invent information not in the profile.
"""


def _ai_answer(question: str, field_type: str, options: list[str], job: dict) -> str:
    opts = f" Options: {options}" if options else ""
    try:
        resp = _gemini.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=(
                f"Candidate profile:\n{json.dumps(_PROFILE, indent=2)}\n\n"
                f"Job: {job['title']} at {job['company']}\n\n"
                f"Question: {question}\nField type: {field_type}{opts}\nAnswer:"
            ),
            config=gtypes.GenerateContentConfig(
                system_instruction=_SCREENING_SYSTEM,
                temperature=0.1,
                max_output_tokens=60,
            ),
        )
        return (resp.text or "").strip()
    except Exception:
        return ""


def _human_delay(lo=400, hi=1200):
    time.sleep(random.uniform(lo / 1000, hi / 1000))


def _get_label(page: Page, el_handle) -> str:
    try:
        el_id = el_handle.get_attribute("id")
        if el_id:
            lbl = page.query_selector(f'label[for="{el_id}"]')
            if lbl:
                return lbl.inner_text().strip()
        return el_handle.evaluate("""el => {
            const legend = el.closest('fieldset')?.querySelector('legend');
            if (legend) return legend.innerText.trim();
            const lbl = el.closest(
              '.artdeco-text-input--container,.fb-dash-form-element,' +
              '.jobs-easy-apply-form-element'
            )?.querySelector('label,legend,span[class*="label"]');
            return lbl ? lbl.innerText.trim() : '';
        }""")
    except Exception:
        return ""


def _fill_step(page: Page, job: dict, pdf_path: str) -> None:
    _human_delay(600, 1400)

    # Resume upload
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        try:
            file_input.set_input_files(pdf_path)
            _human_delay(800, 1600)
        except Exception:
            pass

    # Text inputs
    for sel in ["input[type='text']", "input[type='tel']",
                "input[type='number']", "textarea"]:
        for el in page.query_selector_all(sel):
            try:
                if not el.is_visible():
                    continue
                if el.input_value().strip():
                    continue   # already filled
                label = _get_label(page, el)
                if not label:
                    continue
                low = label.lower()
                answer = next(
                    (v for k, v in {
                        "first": _PROFILE["firstName"],
                        "last":  _PROFILE["lastName"],
                        "email": _PROFILE["email"],
                        "phone": _PROFILE["phone"],
                        "gpa":   _PROFILE["gpa"],
                    }.items() if k in low and v),
                    None
                ) or _ai_answer(label, "text", [], job)
                if answer:
                    el.fill(answer)
                    _human_delay(150, 500)
            except Exception:
                continue

    # Dropdowns
    for el in page.query_selector_all("select"):
        try:
            if not el.is_visible():
                continue
            label = _get_label(page, el)
            opts = el.evaluate(
                "el => [...el.options].map(o=>o.text).filter(t=>t.trim())"
            )
            answer = _ai_answer(label, "select", opts, job)
            real = [o for o in opts if not re.search(r"select|choose|--", o, re.I)]
            if answer and answer in opts:
                el.select_option(label=answer)
            elif real:
                el.select_option(label=real[0])
            _human_delay(150, 400)
        except Exception:
            continue

    # Radio groups
    groups: dict[str, list] = {}
    for el in page.query_selector_all("input[type='radio']"):
        try:
            groups.setdefault(el.get_attribute("name") or "?", []).append(el)
        except Exception:
            pass
    for radios in groups.values():
        try:
            if any(r.is_checked() for r in radios):
                continue
            labels = [_get_label(page, r) or (r.get_attribute("value") or "") for r in radios]
            q      = _get_label(page, radios[0])
            ans    = _ai_answer(q, "radio", labels, job)
            for r, lbl in zip(radios, labels):
                if ans.lower() in lbl.lower() or lbl.lower() in ans.lower():
                    r.click()
                    _human_delay(150, 400)
                    break
        except Exception:
            continue


def _click_primary(page: Page) -> str:
    for sel, action in [
        ('[aria-label="Submit application"]',     "submit"),
        ('button:has-text("Submit application")', "submit"),
        ('button:has-text("Submit")',             "submit"),
        ('[aria-label="Continue to next step"]',  "next"),
        ('button:has-text("Next")',               "next"),
        ('button:has-text("Review")',             "review"),
        ('button:has-text("Done")',               "done"),
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible() and btn.is_enabled():
            btn.click()
            _human_delay(1000, 2500)
            return action
    return "unknown"


def _is_success(page: Page) -> bool:
    try:
        return bool(
            page.query_selector(".artdeco-inline-feedback--success")
            or page.query_selector('[data-test-form-success]')
            or "application was sent" in page.content().lower()
        )
    except Exception:
        return False


def _build_context(pw, browser):
    """Return (context, tmp_state_path | None) using available auth."""
    auth_b64 = os.environ.get("LINKEDIN_AUTH_STATE", "").strip()
    li_at    = os.environ.get("LINKEDIN_COOKIE", "").strip()

    ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    vp = {"width": 1280, "height": 900}

    if auth_b64:
        state_json = base64.b64decode(auth_b64).decode()
        tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        tf.write(state_json)
        tf.close()
        ctx = browser.new_context(storage_state=tf.name, user_agent=ua, viewport=vp)
        return ctx, tf.name

    if li_at:
        ctx = browser.new_context(user_agent=ua, viewport=vp)
        ctx.add_cookies([{
            "name": "li_at", "value": li_at,
            "domain": ".linkedin.com", "path": "/",
            "httpOnly": True, "secure": True,
        }])
        return ctx, None

    return None, None


def apply(job: dict, pdf_path: str) -> dict:
    """Attempt LinkedIn Easy Apply. Returns {"status": str, "message": str}."""
    if "linkedin.com" not in job.get("url", ""):
        return {"status": "skip", "message": "Not a LinkedIn URL."}

    if not (os.environ.get("LINKEDIN_AUTH_STATE") or os.environ.get("LINKEDIN_COOKIE")):
        return {"status": "no_auth",
                "message": "Set LINKEDIN_AUTH_STATE or LINKEDIN_COOKIE secret."}

    tmp_state = None
    result = {"status": "failed", "message": "Unknown error"}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            ctx, tmp_state = _build_context(pw, browser)
            if ctx is None:
                return {"status": "no_auth", "message": "Auth build failed."}

            page = ctx.new_page()
            page.goto(job["url"], wait_until="domcontentloaded", timeout=60_000)
            _human_delay(1500, 3000)

            easy_btn = (
                page.query_selector('button.jobs-apply-button')
                or page.query_selector('button:has-text("Easy Apply")')
            )
            if not easy_btn or "Easy Apply" not in (easy_btn.inner_text() or ""):
                result = {"status": "external",
                          "message": "No Easy Apply — external ATS."}
            else:
                easy_btn.click()
                _human_delay(1500, 2500)
                page.wait_for_selector(
                    ".jobs-easy-apply-modal, [data-test-modal]", timeout=15_000
                )
                applied = False
                for _ in range(12):
                    _fill_step(page, job, pdf_path)
                    action = _click_primary(page)
                    if action in ("submit", "done"):
                        _human_delay(2000, 4000)
                        applied = _is_success(page)
                        break
                    if action == "unknown":
                        break

                result = (
                    {"status": "applied",  "message": "Submitted via Easy Apply."}
                    if applied else
                    {"status": "failed",   "message": "Couldn't complete the form."}
                )
        except Exception as exc:
            result = {"status": "failed", "message": str(exc)}
        finally:
            try:
                browser.close()
            except Exception:
                pass

    if tmp_state:
        try:
            os.unlink(tmp_state)
        except Exception:
            pass
    return result
