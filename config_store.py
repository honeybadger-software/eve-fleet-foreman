"""
config_store.py  --  local settings + token storage for EVE Fleet Foreman.

  foreman_config.json  ->  your ESI Client ID (public, not a secret)
  tokens.json          ->  per-character access/refresh tokens (SENSITIVE)

Both live next to the app and are .gitignored. With PKCE there is no client
SECRET to store, which is the correct/safe design for a distributed app.
"""
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "foreman_config.json")
TOKENS_PATH = os.path.join(DIR, "tokens.json")

# Optional: ship a default Client ID so end-users don't have to register their own
# EVE app. The Client ID is PUBLIC (not a secret); PKCE means there's no secret to
# leak. A user's own saved foreman_config.json always overrides this.
BUNDLED_CLIENT_ID = ""


def _load(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            return {}
    return {}


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---- client id ----
def load_config():
    return _load(CONFIG_PATH)


def get_client_id():
    return (load_config().get("client_id") or BUNDLED_CLIENT_ID or "").strip()


def set_client_id(client_id):
    cfg = load_config()
    cfg["client_id"] = (client_id or "").strip()
    _save(CONFIG_PATH, cfg)


# ---- character tokens ----
def load_tokens():
    return _load(TOKENS_PATH)


def upsert_token(char_id, record):
    toks = load_tokens()
    toks[str(char_id)] = record
    _save(TOKENS_PATH, toks)


def remove_token(char_id):
    toks = load_tokens()
    toks.pop(str(char_id), None)
    _save(TOKENS_PATH, toks)
