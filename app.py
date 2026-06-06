"""
EVE Fleet Foreman  --  fleet-mining assistant.

EULA-safe: reads public Jita market data + CCP's static data + (with your login)
your own read-only Mining Ledger. No game hooks, no automation, no broadcasting.

Tabs:
  1. What to Mine     -- ores ranked by ISK/m³, RAW vs REFINED, for your skills
  2. Fleet Yield      -- fleet m³/min, ISK/hour, time-to-fill, hauler trips
  3. Refine           -- sell-raw vs reprocess verdict + mineral breakdown
  4. Mining Ledger ⭐  -- log in with EVE; auto-pull what each pilot mined + fair split
  5. Appraise & Split -- value a pile of ore and split it across the fleet

Run:  python app.py   (or run_eve_foreman.bat)  ->  http://localhost:8088
"""
import os
import time

from fastapi.responses import HTMLResponse
from nicegui import app as fastapi_app
from nicegui import ui

import ore_data
import ships as ships_mod
import market
import refine
import config_store
import esi_sso
import esi_client

ALL_TYPE_IDS = ore_data.ORE_TYPE_IDS + ore_data.MINERAL_TYPE_IDS

state = {"prices": {}, "updated": "never", "best_ore": None, "ledgers": {}, "_char_ids": None}


def fmt(n):
    try:
        return f"{float(n):,.0f}"
    except (TypeError, ValueError):
        return "-"


# ----------------------------------------------------- EVE SSO callback route
@fastapi_app.get("/callback")
def sso_callback(code: str = "", state: str = ""):
    """CCP redirects the browser here after login; we swap the code for tokens."""
    try:
        rec = esi_sso.complete_login(config_store.get_client_id(), code, state)
        config_store.upsert_token(rec["character_id"], rec)
        msg = f"✅ Logged in as <b>{rec['character_name']}</b>. Close this tab and return to Foreman."
    except Exception as e:  # noqa: BLE001
        msg = f"❌ Login failed: {e}"
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>"
        f"<h2>⛏ EVE Fleet Foreman</h2><p style='font-size:18px'>{msg}</p></body></html>")


def get_efficiency():
    return refine.effective_efficiency(
        base_pct=eff_base.value or 0, reproc=eff_reproc.value or 0,
        reproc_eff=eff_reproc_eff.value or 0, ore_specific=eff_ore.value or 0,
        implant_pct=eff_implant.value or 0)


# ---------------------------------------------------------------- data + paint
def refresh():
    try:
        state["prices"] = market.get_prices(ALL_TYPE_IDS, max_age=0)
        state["updated"] = time.strftime("%H:%M:%S")
    except Exception as e:  # noqa: BLE001
        ui.notify(f"Price fetch failed: {e}", type="negative")
        return
    repaint()


def repaint():
    prices, eff = state["prices"], get_efficiency()
    eff_label.text = f"Effective reprocessing: {eff * 100:,.1f}%"
    rows = []
    for o in ore_data.ORES:
        vol = o["volume"] or 0.0001
        raw = prices.get(o["type_id"], {}).get("sell", 0.0)
        refined = refine.refined_value_per_unit(o["type_id"], eff, prices, basis="sell")
        raw_m3, ref_m3 = raw / vol, refined / vol
        rows.append({"name": o["name"], "vol": f"{vol:g}", "raw_m3": raw_m3,
                     "ref_m3": ref_m3, "best": max(raw_m3, ref_m3),
                     "verdict": "Refine" if ref_m3 > raw_m3 else "Sell raw"})
    rows.sort(key=lambda r: r["best"], reverse=True)
    if rows:
        state["best_ore"] = next((o for o in ore_data.ORES if o["name"] == rows[0]["name"]), None)
    price_table.rows = [{"name": r["name"], "vol": r["vol"], "raw_m3": fmt(r["raw_m3"]),
                         "ref_m3": fmt(r["ref_m3"]), "best": fmt(r["best"]), "verdict": r["verdict"]}
                        for r in rows]
    price_table.update()
    updated_label.text = f"Jita updated {state['updated']}"
    if ore_select.value is None and state["best_ore"]:
        ore_select.value = state["best_ore"]["name"]
    if refine_ore.value is None and state["best_ore"]:
        refine_ore.value = state["best_ore"]["name"]
    recompute_yield()
    recompute_refine()
    recompute_appraise()


# ---------------------------------------------------------------------- layout
ui.dark_mode().enable()
ui.colors(primary="#f5a623")

with ui.header().classes("items-center"):
    ui.label("⛏  EVE Fleet Foreman").classes("text-2xl font-bold")
    ui.space()
    updated_label = ui.label("Jita updated never").classes("text-sm opacity-70")
    ui.button(icon="refresh", on_click=refresh).props("flat round color=white")

with ui.expansion("⚙  Your reprocessing setup (skills / structure)", icon="settings").classes("w-full"):
    with ui.row().classes("items-center gap-3 flex-wrap"):
        eff_base = ui.number(label="Base yield %", value=50, min=0, max=90, step=1).props("dense") \
            .tooltip("≈50 at a hisec NPC station; higher in a rigged Athanor/Tatara")
        eff_reproc = ui.number(label="Reprocessing", value=5, min=0, max=5, step=1).props("dense").tooltip("+3%/level")
        eff_reproc_eff = ui.number(label="Reproc. Efficiency", value=5, min=0, max=5, step=1).props("dense").tooltip("+2%/level")
        eff_ore = ui.number(label="Ore-specific skill", value=4, min=0, max=5, step=1).props("dense").tooltip("e.g. Veldspar Processing, +2%/level")
        eff_implant = ui.number(label="Implant %", value=0, min=0, max=4, step=1).props("dense").tooltip("RX-801/802/804 = 1/2/4%")
        eff_label = ui.label("Effective reprocessing: —").classes("font-bold text-amber-400")
    for w in (eff_base, eff_reproc, eff_reproc_eff, eff_ore, eff_implant):
        w.on_value_change(lambda e: repaint())

with ui.tabs().classes("w-full") as tabs:
    t_mine = ui.tab("What to Mine", icon="diamond")
    t_yield = ui.tab("Fleet Yield", icon="groups")
    t_refine = ui.tab("Refine", icon="science")
    t_ledger = ui.tab("Mining Ledger ⭐", icon="receipt_long")
    t_split = ui.tab("Appraise & Split", icon="paid")

with ui.tab_panels(tabs, value=t_mine).classes("w-full"):

    # ---------- TAB 1: What to Mine ----------
    with ui.tab_panel(t_mine):
        ui.label("Ores ranked by best ISK/m³ for YOUR skills — raw vs reprocess. Mine from the top.").classes("opacity-80")
        price_table = ui.table(row_key="name", rows=[], columns=[
            {"name": "name", "label": "Ore", "field": "name", "align": "left", "sortable": True},
            {"name": "vol", "label": "m³/unit", "field": "vol", "align": "right"},
            {"name": "raw_m3", "label": "Raw ISK/m³", "field": "raw_m3", "align": "right", "sortable": True},
            {"name": "ref_m3", "label": "Refined ISK/m³", "field": "ref_m3", "align": "right", "sortable": True},
            {"name": "best", "label": "Best ISK/m³", "field": "best", "align": "right", "sortable": True},
            {"name": "verdict", "label": "Do", "field": "verdict", "align": "center"},
        ]).classes("w-full").props("dense")

    # ---------- TAB 2: Fleet Yield ----------
    with ui.tab_panel(t_yield):
        ui.label("Set how many of each ship are in the fleet. Tune yield/hold to your skills.").classes("opacity-80")
        ship_inputs = {}
        with ui.grid(columns=4).classes("gap-x-4 gap-y-1 items-center"):
            for head in ("Ship", "Count", "Yield m³/min", "Ore hold m³"):
                ui.label(head).classes("font-bold")
            for s in ships_mod.SHIPS:
                ui.label(s["name"] + ("  ✨boost" if s["booster"] else ""))
                c = ui.number(value=0, min=0, step=1).props("dense")
                y = ui.number(value=s["yield"], min=0, step=10).props("dense")
                h = ui.number(value=s["hold"], min=0, step=500).props("dense")
                for w in (c, y, h):
                    w.on_value_change(lambda e: recompute_yield())
                ship_inputs[s["name"]] = {"count": c, "yield": y, "hold": h, "booster": s["booster"]}
        with ui.row().classes("items-center mt-3 gap-4"):
            boost_on = ui.checkbox("Fleet boost (Orca/Porpoise burst)", value=False)
            boost_pct = ui.number(label="Boost %", value=ships_mod.DEFAULT_BOOST_PCT, min=0, step=1).props("dense")
            ore_select = ui.select(options=[o["name"] for o in ore_data.ORES], label="Target ore",
                                   with_input=True).props("dense").style("min-width:160px")
            hauler_cap = ui.number(label="Hauler m³", value=30000, min=1, step=1000).props("dense")
        for w in (boost_on, boost_pct, ore_select, hauler_cap):
            w.on_value_change(lambda e: recompute_yield())
        with ui.card().classes("mt-3 w-full"):
            yield_out = ui.markdown("Enter ship counts to see fleet output.")

    # ---------- TAB 3: Refine ----------
    with ui.tab_panel(t_refine):
        ui.label("Sell raw or reprocess? Pick an ore + amount; uses your setup above.").classes("opacity-80")
        with ui.row().classes("items-center gap-4"):
            refine_ore = ui.select(options=[o["name"] for o in ore_data.ORES], label="Ore",
                                   with_input=True).props("dense").style("min-width:160px")
            refine_units = ui.number(label="Units", value=100000, min=0, step=1000).props("dense")
        for w in (refine_ore, refine_units):
            w.on_value_change(lambda e: recompute_refine())
        with ui.card().classes("mt-3 w-full"):
            refine_out = ui.markdown("Pick an ore to compare.")

    # ---------- TAB 4: Mining Ledger ⭐ ----------
    with ui.tab_panel(t_ledger):
        ui.label("Log in with EVE to auto-pull each pilot's last ~30 days of mining, "
                 "valued at live Jita prices, with a fair split. Read-only — Foreman can never act in-game.").classes("opacity-80")

        with ui.expansion("① First-time setup — paste your ESI Client ID", icon="key").classes("w-full"):
            ui.markdown(
                "Register a free app at **developers.eveonline.com** → *Create New Application* → "
                "**Connection Type: Authentication & API Access**, tick the **mining** scopes, "
                f"**Callback URL** = `{esi_sso.CALLBACK_URL}`. It gives you a **Client ID** — paste it here. "
                "(No secret needed — Foreman uses PKCE.)")
            with ui.row().classes("items-center gap-2"):
                client_id_input = ui.input(label="ESI Client ID", value=config_store.get_client_id()) \
                    .props("dense").style("min-width:340px")
                ui.button("Save", on_click=lambda: _save_client_id()).props("color=primary")

        with ui.row().classes("items-center gap-3 mt-2"):
            ui.button("Log in with EVE Online", icon="login", on_click=lambda: _start_login()).props("color=primary")
            ui.button("Pull mining data", icon="cloud_download", on_click=lambda: _pull_ledgers()).props("outline")
            ui.button("Load sample data", icon="preview", on_click=lambda: _load_sample()).props("flat")
        login_status = ui.row().classes("items-center gap-2 mt-1")
        ledger_container = ui.column().classes("w-full mt-3")

    # ---------- TAB 5: Appraise & Split ----------
    with ui.tab_panel(t_split):
        ui.label("Paste what the fleet mined — one per line:  “OreName  quantity”.").classes("opacity-80")
        appraise_in = ui.textarea(placeholder="Veldspar 250000\nScordite 120000\nKernite 40000") \
            .classes("w-full").props("outlined autogrow")
        with ui.row().classes("items-center gap-4"):
            members = ui.number(label="Fleet members", value=3, min=1, step=1).props("dense")
            price_basis = ui.toggle({"sell": "Sell value", "buy": "Buy value"}, value="buy")
        for w in (appraise_in, members, price_basis):
            w.on_value_change(lambda e: recompute_appraise())
        with ui.card().classes("mt-3 w-full"):
            appraise_out = ui.markdown("Paste ore amounts above.")


# ------------------------------------------------------------- ledger handlers
def _save_client_id():
    config_store.set_client_id(client_id_input.value or "")
    ui.notify("Client ID saved", type="positive")


def _open_url(url):
    """Open a URL in a new browser tab, across NiceGUI versions."""
    if hasattr(ui, "navigate") and hasattr(ui.navigate, "to"):
        ui.navigate.to(url, new_tab=True)
    else:  # older NiceGUI
        ui.open(url, new_tab=True)


def _start_login():
    cid = config_store.get_client_id()
    if not cid:
        ui.notify("Paste your Client ID and hit Save first.", type="warning")
        return
    _open_url(esi_sso.begin_login(cid))


def _render_login_status():
    login_status.clear()
    with login_status:
        toks = config_store.load_tokens()
        if not toks:
            ui.label("Not logged in.").classes("opacity-60")
            return
        ui.label("Logged in:").classes("opacity-70")
        for cid_, rec in toks.items():
            with ui.row().classes("items-center gap-1"):
                ui.label(rec.get("character_name", cid_)).classes("px-2 py-1 bg-amber-800 rounded text-sm")
                ui.button(icon="logout", on_click=lambda c=cid_: _logout(c)) \
                    .props("flat dense round size=sm").tooltip("Log out")


def _logout(char_id):
    config_store.remove_token(char_id)
    state["ledgers"].pop(str(char_id), None)
    state["_char_ids"] = None  # force status re-render
    _render_ledgers()


def _login_poll():
    ids = sorted(config_store.load_tokens().keys())
    if ids != state["_char_ids"]:
        state["_char_ids"] = ids
        _render_login_status()


def _pull_ledgers():
    cid = config_store.get_client_id()
    if not cid:
        ui.notify("Set your Client ID first.", type="warning")
        return
    toks = config_store.load_tokens()
    if not toks:
        ui.notify("Log in with EVE first.", type="warning")
        return
    ui.notify("Pulling mining ledgers from ESI…")
    raw, type_ids, sys_ids = {}, set(), set()
    try:
        for char_id in list(toks.keys()):
            rows = esi_client.get_mining_ledger(cid, char_id)
            raw[char_id] = rows
            for r in rows:
                type_ids.add(r["type_id"])
                sys_ids.add(r["solar_system_id"])
    except Exception as e:  # noqa: BLE001
        ui.notify(f"ESI error: {e}", type="negative")
        return
    names = esi_client.resolve_names(list(type_ids | sys_ids)) if (type_ids or sys_ids) else {}
    prices = market.get_prices(list(type_ids), max_age=120) if type_ids else {}
    ledgers = {}
    for char_id, rows in raw.items():
        rec = config_store.load_tokens().get(char_id, {})
        by_ore, total = {}, 0.0
        for r in rows:
            price = prices.get(r["type_id"], {}).get("sell", 0.0)
            val = price * r["quantity"]
            total += val
            o = by_ore.setdefault(r["type_id"], {"name": names.get(r["type_id"], r["type_id"]), "qty": 0, "isk": 0.0})
            o["qty"] += r["quantity"]
            o["isk"] += val
        ledgers[char_id] = {"name": rec.get("character_name", char_id), "total": total,
                            "by_ore": by_ore, "days": len({r["date"] for r in rows})}
    state["ledgers"] = ledgers
    _render_ledgers()
    ui.notify("Mining ledgers updated.", type="positive")


SAMPLE_LEDGER = {
    "Mining Mike": {"Veldspar": 2_400_000, "Scordite": 820_000, "Kernite": 140_000},
    "Alt Anderson": {"Veldspar": 1_150_000, "Plagioclase": 360_000, "Omber": 90_000},
    "Corpmate Cara": {"Omber": 520_000, "Kernite": 210_000, "Gneiss": 28_000},
}


def _load_sample():
    """Populate the ledger with realistic demo data (no login needed) so you can
    see the layout + fair split — also handy for marketing screenshots."""
    by_name = {o["name"]: o for o in ore_data.ORES}
    ids = list({by_name[n]["type_id"] for ores in SAMPLE_LEDGER.values() for n in ores})
    try:
        prices = market.get_prices(ids, max_age=120)
    except Exception:  # noqa: BLE001
        prices = state.get("prices", {})
    ledgers = {}
    for i, (pilot, ores) in enumerate(SAMPLE_LEDGER.items()):
        by_ore, total = {}, 0.0
        for oname, qty in ores.items():
            o = by_name[oname]
            isk = prices.get(o["type_id"], {}).get("sell", 0.0) * qty
            total += isk
            by_ore[o["type_id"]] = {"name": oname, "qty": qty, "isk": isk}
        ledgers[f"sample{i}"] = {"name": pilot, "total": total, "by_ore": by_ore, "days": 14}
    state["ledgers"] = ledgers
    _render_ledgers()
    ui.notify("Loaded sample data (demo). Hit 'Pull mining data' for your real ledger.", type="info")


def _render_ledgers():
    ledger_container.clear()
    ledgers = state.get("ledgers", {})
    with ledger_container:
        if not ledgers:
            ui.label("No data yet — log in, then hit ‘Pull mining data’.").classes("opacity-60")
            return
        combined = sum(l["total"] for l in ledgers.values())
        n = len(ledgers)
        even = combined / n if n else 0
        with ui.card().classes("w-full"):
            md = [f"### Fleet total (last ~30 days): **{fmt(combined)} ISK**  —  {n} pilot(s)"]
            for _, l in sorted(ledgers.items(), key=lambda kv: kv[1]["total"], reverse=True):
                share = (l["total"] / combined * 100) if combined else 0
                md.append(f"- **{l['name']}** — mined **{fmt(l['total'])} ISK** ({share:,.1f}%)")
            md.append(f"\n**Even split:** {fmt(even)} ISK each  ·  "
                      f"**By contribution:** each pilot keeps their own mined value above.")
            ui.markdown("\n".join(md))
        for _, l in sorted(ledgers.items(), key=lambda kv: kv[1]["total"], reverse=True):
            with ui.expansion(f"{l['name']} — {fmt(l['total'])} ISK", icon="person").classes("w-full"):
                rows = [{"ore": o["name"], "qty": f'{o["qty"]:,}', "isk": fmt(o["isk"])}
                        for o in sorted(l["by_ore"].values(), key=lambda x: x["isk"], reverse=True)]
                ui.table(row_key="ore", rows=rows, columns=[
                    {"name": "ore", "label": "Ore", "field": "ore", "align": "left"},
                    {"name": "qty", "label": "Units", "field": "qty", "align": "right"},
                    {"name": "isk", "label": "ISK (Jita sell)", "field": "isk", "align": "right"},
                ]).props("dense").classes("w-full")


# ------------------------------------------------------------------ computations
def recompute_yield():
    total_yield = total_hold = 0.0
    for w in ship_inputs.values():
        cnt = w["count"].value or 0
        if cnt <= 0:
            continue
        total_yield += cnt * (w["yield"].value or 0)
        total_hold += cnt * (w["hold"].value or 0)
    if boost_on.value:
        total_yield *= 1 + (boost_pct.value or 0) / 100.0
    ore_name = ore_select.value or (state["best_ore"]["name"] if state["best_ore"] else None)
    isk_per_m3 = 0.0
    if ore_name:
        o = next((x for x in ore_data.ORES if x["name"] == ore_name), None)
        if o:
            vol = o["volume"] or 0.0001
            raw = state["prices"].get(o["type_id"], {}).get("sell", 0.0) / vol
            refined = refine.refined_value_per_unit(o["type_id"], get_efficiency(), state["prices"]) / vol
            isk_per_m3 = max(raw, refined)
    isk_per_hour = total_yield * 60 * isk_per_m3
    fill_min = (total_hold / total_yield) if total_yield > 0 else 0.0
    trips = total_hold / (hauler_cap.value or 1)
    yield_out.content = (
        f"### Fleet output\n"
        f"- **Combined yield:** {total_yield:,.0f} m³/min  ({total_yield * 60:,.0f} m³/hour)\n"
        f"- **Target ore:** {ore_name or '—'}  (best {fmt(isk_per_m3)} ISK/m³)\n"
        f"- **Income:** **{fmt(isk_per_hour)} ISK/hour**\n"
        f"- **Combined ore hold:** {total_hold:,.0f} m³ — fills in **{fill_min:,.1f} min**\n"
        f"- **Hauler trips to clear holds:** {trips:,.1f}  (@ {fmt(hauler_cap.value)} m³ each)\n")
    if not boost_on.value:
        yield_out.content += "\n_Tip: tick Fleet boost if an Orca/Porpoise is running bursts._"


def recompute_refine():
    name = refine_ore.value
    o = next((x for x in ore_data.ORES if x["name"] == name), None) if name else None
    if not o:
        refine_out.content = "Pick an ore to compare."
        return
    units = int(refine_units.value or 0)
    eff, prices = get_efficiency(), state["prices"]
    raw_isk = prices.get(o["type_id"], {}).get("sell", 0.0) * units
    mins, ref_isk = refine.refined_value_of_units(o["type_id"], units, eff, prices, basis="sell")
    better = "REFINE" if ref_isk > raw_isk else "SELL RAW"
    diff = abs(ref_isk - raw_isk)
    pct = (diff / raw_isk * 100) if raw_isk else 0
    breakdown = "\n".join(
        f"  - {refine.MINERAL_NAME.get(mid, mid)}: {q:,.0f} × {fmt(prices.get(mid, {}).get('sell', 0))} "
        f"= {fmt(q * prices.get(mid, {}).get('sell', 0))} ISK"
        for mid, q in mins.items() if q > 0)
    refine_out.content = (
        f"### {name} × {units:,.0f}  (reprocessing at {eff * 100:,.1f}%)\n"
        f"- **Sell raw:** {fmt(raw_isk)} ISK\n"
        f"- **Reprocess & sell minerals:** {fmt(ref_isk)} ISK\n\n"
        f"## → {better}  ({'+' if better == 'REFINE' else '−'}{fmt(diff)} ISK, {pct:,.1f}%)\n\n"
        f"**Minerals produced:**\n{breakdown or '  (none)'}")


def recompute_appraise():
    text = appraise_in.value or ""
    basis = price_basis.value or "buy"
    total, lines, unknown = 0.0, [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)
        if len(parts) != 2:
            continue
        name_part, qty_part = parts
        try:
            qty = float(qty_part.replace(",", ""))
        except ValueError:
            continue
        o = next((x for x in ore_data.ORES if x["name"].lower() == name_part.lower()), None)
        if not o:
            unknown.append(name_part)
            continue
        unit = state["prices"].get(o["type_id"], {}).get(basis, 0.0)
        total += unit * qty
        lines.append(f"- {o['name']}: {qty:,.0f} × {fmt(unit)} = {fmt(unit * qty)} ISK")
    m = int(members.value or 1)
    md = (f"### Total ({basis} value): {fmt(total)} ISK\n"
          f"### Per member (÷{m}): **{fmt(total / m if m else total)} ISK**\n\n")
    if lines:
        md += "\n".join(lines)
    if unknown:
        md += f"\n\n_Unrecognized: {', '.join(sorted(set(unknown)))}_"
    appraise_out.content = md


# --------------------------------------------------------- first load + timers
ui.timer(0.1, refresh, once=True)
ui.timer(0.2, _render_login_status, once=True)
ui.timer(300, refresh)
ui.timer(3.0, _login_poll)  # reflect new logins from the SSO callback

with ui.footer().classes("bg-transparent items-center gap-2"):
    ui.label("⛏ EVE Fleet Foreman").classes("text-xs opacity-80")
    ui.label("· built by").classes("text-xs opacity-50")
    ui.link("Honeybadger Software", "https://honeybadger.software", new_tab=True).classes("text-xs text-amber-400")
    ui.space()
    ui.label("EVE Online & the EVE logo are registered trademarks of CCP hf. "
             "Unofficial tool, not affiliated with CCP. Market data: Fuzzwork.").classes("text-xs opacity-50")

if __name__ in {"__main__", "__mp_main__"}:
    show = os.environ.get("FOREMAN_SHOW", "1") != "0"
    # Default 8088 must match your EVE app's callback URL; override only for dev/testing.
    port = int(os.environ.get("FOREMAN_PORT", "8088"))
    ui.run(title="EVE Fleet Foreman", port=port, reload=False, show=show)
