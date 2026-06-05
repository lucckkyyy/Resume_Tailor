"""
ONE-TIME local setup. Run this on your own computer to capture your LinkedIn
session so the CI can apply without ever seeing your password.

  pip install -r requirements.txt
  playwright install chromium
  python get_linkedin_state.py

A browser window opens. Log into LinkedIn normally (including any 2FA).
Once you see your LinkedIn feed, come back here and press Enter.
The script prints a base64 string — store it as the GitHub Secret LINKEDIN_AUTH_STATE.

LinkedIn auth typically lasts 60 days. Re-run when Easy Apply stops working.
"""

import base64
import json
import pathlib

from playwright.sync_api import sync_playwright


def main() -> None:
    out = pathlib.Path("linkedin_state.json")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)   # headed so you can log in
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.goto("https://www.linkedin.com/login")

        print("\nA browser window just opened.")
        print("Log into LinkedIn (complete any 2FA).")
        print("Once you can see your LinkedIn feed, press Enter here.\n")
        input("Press Enter after you're logged in → ")

        ctx.storage_state(path=str(out))
        browser.close()

    state_bytes = out.read_bytes()
    b64 = base64.b64encode(state_bytes).decode()

    print("\n======= COPY THIS INTO GITHUB SECRET: LINKEDIN_AUTH_STATE =======\n")
    print(b64)
    print("\n==================================================================")
    print(f"\n(Also saved locally as {out} — add it to .gitignore, never commit it.)\n")

    # Append to .gitignore
    gi = pathlib.Path(".gitignore")
    if gi.exists() and "linkedin_state.json" not in gi.read_text():
        gi.write_text(gi.read_text() + "\nlinkedin_state.json\n")


if __name__ == "__main__":
    main()
