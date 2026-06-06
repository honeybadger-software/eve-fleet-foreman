"""
market.py  --  live Jita market prices via the public Fuzzwork aggregates API.

This is read-only public market data -- the same numbers anyone sees on the
in-game market. No login, no game hooks, fully EULA-safe.

  get_prices([type_ids]) -> { type_id: {"sell": float, "buy": float} }
    sell = cheapest SELL order in Jita  (what the item is worth / costs to buy)
    buy  = highest  BUY  order in Jita  (what you'd get dumping it instantly)
"""
import time
import requests

FUZZWORK = "https://market.fuzzwork.co.uk/aggregates/"
JITA_4_4_STATION = 60003760  # Jita IV - Moon 4 - Caldari Navy Assembly Plant
HEADERS = {"User-Agent": "eve_foreman/0.1 (honeybadger.software) personal fleet tool"}

# tiny in-memory cache so rapid UI refreshes don't hammer the API
_cache = {"key": None, "ts": 0.0, "data": {}}


def get_prices(type_ids, station=JITA_4_4_STATION, max_age=60):
    """Fetch Jita buy/sell for the given type IDs. Cached for `max_age` seconds."""
    now = time.time()
    key = (station, tuple(sorted(type_ids)))
    if _cache["key"] == key and (now - _cache["ts"]) < max_age:
        return _cache["data"]

    ids = ",".join(str(t) for t in type_ids)
    r = requests.get(FUZZWORK, params={"station": station, "types": ids},
                     headers=HEADERS, timeout=30)
    r.raise_for_status()
    raw = r.json()

    out = {}
    for tid, agg in raw.items():
        sell_min = agg.get("sell", {}).get("min")
        buy_max = agg.get("buy", {}).get("max")
        out[int(tid)] = {
            "sell": float(sell_min) if sell_min not in (None, "0", 0) else 0.0,
            "buy": float(buy_max) if buy_max not in (None, "0", 0) else 0.0,
        }

    _cache.update(key=key, ts=now, data=out)
    return out
