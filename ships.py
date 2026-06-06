"""
ships.py  --  default mining-ship stats.

IMPORTANT: every number here is a sensible MID-SKILL starting point, not gospel.
Real yield/hold depend on your fit, skills, implants and modules -- so all of
these are EDITABLE live in the app. Tune them once to match your characters.

  hold   = ore-hold capacity in m3 (how much before you must dump to a hauler)
  yield  = mining rate in m3/min  (ballpark, T2 lasers, decent skills, no boost)
  booster= True for command ships that run Mining Foreman Bursts (Orca/Porpoise)
"""

SHIPS = [
    # name         hold(m3)  yield(m3/min)  booster
    {"name": "Venture",   "hold": 5000,   "yield": 450,  "booster": False},
    {"name": "Procurer",  "hold": 12000,  "yield": 800,  "booster": False},
    {"name": "Retriever", "hold": 22000,  "yield": 1100, "booster": False},
    {"name": "Covetor",   "hold": 7000,   "yield": 1400, "booster": False},
    {"name": "Skiff",     "hold": 15000,  "yield": 1100, "booster": False},
    {"name": "Mackinaw",  "hold": 28000,  "yield": 1300, "booster": False},
    {"name": "Hulk",      "hold": 8500,   "yield": 1700, "booster": False},
    {"name": "Porpoise",  "hold": 10000,  "yield": 200,  "booster": True},
    {"name": "Orca",      "hold": 50000,  "yield": 200,  "booster": True},
]

SHIP_BY_NAME = {s["name"]: s for s in SHIPS}

# Default fleet yield bonus from a Mining Foreman Burst (Mining Laser Field
# Enhancement). ~37% is a good T2-burst-with-skills figure; editable in the UI.
DEFAULT_BOOST_PCT = 37.0
