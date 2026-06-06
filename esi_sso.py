"""
esi_sso.py  --  EVE Online SSO (OAuth2 + PKCE) login.

Why PKCE: a distributed/sellable app can't safely embed a client secret, so we
use Authorization-Code-with-PKCE, which needs only a public Client ID. The user
logs in on CCP's own site; we only ever receive a revocable token, never a password.

Flow:
  begin_login(client_id)        -> URL to open in the browser (CCP login)
  complete_login(cid, code, st) -> exchange the redirect's ?code for tokens
  refresh(client_id, refresh)   -> get a fresh access token when one expires
"""
import base64
import hashlib
import json
import secrets as randsecrets
import time
import urllib.parse

import requests

AUTHORIZE_URL = "https://login.eveonline.com/v2/oauth/authorize/"
TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
CALLBACK_URL = "http://localhost:8088/callback"
SCOPES = [
    "esi-industry.read_character_mining.v1",     # personal mining ledger
    "esi-industry.read_corporation_mining.v1",   # corp/structure ledger (corp mode, later)
]
HEADERS = {"User-Agent": "eve_foreman/0.1 (honeybadger.software) personal fleet tool"}

# state -> code_verifier, for in-flight logins
_pending = {}


def _b64url(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode()


def begin_login(client_id):
    """Return the CCP authorize URL to open in the browser."""
    verifier = _b64url(randsecrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(randsecrets.token_bytes(16))
    _pending[state] = verifier
    params = {
        "response_type": "code",
        "redirect_uri": CALLBACK_URL,
        "client_id": client_id,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)


def _token_request(data):
    r = requests.post(TOKEN_URL, data=data,
                      headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
                      timeout=30)
    r.raise_for_status()
    return r.json()


def _record_from_token(tok, fallback_refresh=None):
    char_id, name = _decode_access_token(tok["access_token"])
    return {
        "character_id": char_id,
        "character_name": name,
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token", fallback_refresh),
        "expires_at": time.time() + tok.get("expires_in", 1200) - 30,
    }


def complete_login(client_id, code, state):
    """Exchange the authorization code (from the redirect) for tokens."""
    verifier = _pending.pop(state, None)
    if verifier is None:
        raise ValueError("Unknown or expired login state (try logging in again)")
    tok = _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "code_verifier": verifier,
    })
    return _record_from_token(tok)


def refresh(client_id, refresh_token):
    """Use a refresh token to mint a new access token."""
    tok = _token_request({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    })
    return _record_from_token(tok, fallback_refresh=refresh_token)


def _decode_access_token(access_token):
    """EVE SSO v2 access tokens are JWTs. Decode the payload to read the character
    id + name. (Local read only; for a shipped build we'd verify against CCP's JWKS.)"""
    payload_b64 = access_token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # pad to multiple of 4
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    sub = payload.get("sub", "")            # "CHARACTER:EVE:123456789"
    char_id = int(sub.split(":")[-1])
    return char_id, payload.get("name", "Unknown")
