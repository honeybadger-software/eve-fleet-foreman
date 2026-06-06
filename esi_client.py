"""
esi_client.py  --  authenticated ESI calls (with auto token-refresh).

  get_mining_ledger(client_id, char_id) -> [{date, quantity, type_id, solar_system_id}, ...]
  resolve_names(ids)                     -> {id: name}  (ore/ice/moon types AND systems)
"""
import time

import requests

import config_store
import esi_sso

ESI = "https://esi.evetech.net/latest"
HEADERS = {"User-Agent": "eve_foreman/0.1 (honeybadger.software) personal fleet tool"}

_name_cache = {}


def _valid_access_token(client_id, char_id):
    """Return a non-expired access token for the character, refreshing if needed."""
    rec = config_store.load_tokens().get(str(char_id))
    if not rec:
        return None
    if rec.get("expires_at", 0) <= time.time():
        rec = esi_sso.refresh(client_id, rec["refresh_token"])
        config_store.upsert_token(char_id, rec)
    return rec["access_token"]


def get_mining_ledger(client_id, char_id):
    """The character's mining ledger (CCP keeps roughly the last 30 days)."""
    token = _valid_access_token(client_id, char_id)
    if not token:
        return []
    out, page = [], 1
    auth = {**HEADERS, "Authorization": f"Bearer {token}"}
    while True:
        r = requests.get(f"{ESI}/characters/{char_id}/mining/",
                         params={"page": page}, headers=auth, timeout=30)
        if r.status_code in (403, 404):
            break
        r.raise_for_status()
        chunk = r.json()
        if not chunk:
            break
        out.extend(chunk)
        if page >= int(r.headers.get("X-Pages", 1)):
            break
        page += 1
    return out


def resolve_names(ids):
    """Resolve a mixed list of type/system ids to names via /universe/names/."""
    ids = [int(i) for i in set(ids)]
    todo = [i for i in ids if i not in _name_cache]
    for i in range(0, len(todo), 1000):  # endpoint accepts up to 1000 ids
        chunk = todo[i:i + 1000]
        try:
            r = requests.post(f"{ESI}/universe/names/", json=chunk, headers=HEADERS, timeout=30)
            if r.ok:
                for item in r.json():
                    _name_cache[item["id"]] = item["name"]
        except requests.RequestException:
            pass
    return {i: _name_cache.get(i, str(i)) for i in ids}
