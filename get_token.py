"""
ONE-TIME local helper. Run this on your own computer (not in GitHub Actions)
to authorize Drive + Docs access and print a long-lived refresh token.

Prereqs:
  1. In Google Cloud Console, create an OAuth client of type "Desktop app".
  2. Download its JSON and save it next to this file as `client_secret.json`.
  3. pip install -r requirements.txt
  4. python get_token.py

It opens a browser, you approve once, and it prints the three values to paste
into your GitHub Actions Secrets: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    # access_type=offline + prompt=consent forces Google to return a refresh token.
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )

    print("\n=========== COPY THESE INTO GITHUB SECRETS ===========\n")
    print(f"GOOGLE_CLIENT_ID     = {creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET = {creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN = {creds.refresh_token}")
    print("\n======================================================\n")
    if not creds.refresh_token:
        print(
            "No refresh token returned. Revoke the app's access at "
            "https://myaccount.google.com/permissions and run this again."
        )


if __name__ == "__main__":
    main()
