"""Google OAuth 2.0 (authorization-code flow). Only used when GOOGLE_* variables are configured."""
import secrets
from urllib.parse import urlencode

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = "openid email profile"  # minimal: identity only, no Drive/Calendar access requested


def is_configured(cfg) -> bool:
    return bool(cfg["GOOGLE_CLIENT_ID"] and cfg["GOOGLE_CLIENT_SECRET"] and cfg["GOOGLE_REDIRECT_URI"])


def new_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(cfg, state: str) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": cfg["GOOGLE_CLIENT_ID"], "redirect_uri": cfg["GOOGLE_REDIRECT_URI"], "response_type": "code",
        "scope": SCOPES, "state": state, "prompt": "select_account", "access_type": "online"})


def fetch_profile(cfg, code: str) -> dict:
    """Exchange the code, then read the verified profile straight from Google over TLS."""
    tok = requests.post(TOKEN_URL, data={
        "code": code, "client_id": cfg["GOOGLE_CLIENT_ID"], "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": cfg["GOOGLE_REDIRECT_URI"], "grant_type": "authorization_code"}, timeout=10)
    tok.raise_for_status()
    access = tok.json()["access_token"]
    info = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access}"}, timeout=10)
    info.raise_for_status()
    return info.json()
