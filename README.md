# EVE Fleet Foreman

![What to Mine: every ore ranked by ISK per m³, raw against reprocessed, from live Jita prices](screenshots/what-to-mine.png)

A free fleet-mining assistant for EVE Online, by [Honey Badger Software](https://honeybadger.software). It answers the questions that decide whether mining pays: what should I mine right now, should I refine or sell, what is the fleet making, and how do we split the ore fairly. It uses live Jita market data and your own Mining Ledger.

**Download:** [EVE-Fleet-Foreman.exe](https://github.com/honeybadger-software/eve-fleet-foreman/releases/latest/download/EVE-Fleet-Foreman.exe) (Windows, no Python needed), or run it from source below.

> **EULA-safe.** Foreman never touches the game client. No memory reading, no input automation, no input broadcasting. It only reads public market data and, if you log in, your own read-only Mining Ledger from CCP's official API. Multiboxing is allowed; input broadcasting and botting are what get people banned, and Foreman does none of that.

## What it does

| Tab | What you get |
|-----|--------------|
| **What to Mine** | Every ore ranked by **ISK per m³** from live Jita prices, raw against reprocessed, for *your* refining skills. Mine from the top down. |
| **Fleet Yield** | Enter your ships (barges, exhumers, plus an Orca/Porpoise boost) and get combined **m³/min, ISK/hour, time to fill and hauler trips**. |
| **Refine** | Pick an ore and an amount for a clear **SELL RAW or REFINE** verdict with the full mineral breakdown. Uses real reprocessing yields from CCP's data. |
| **Mining Ledger** | Log in with EVE and pull each pilot's last ~30 days of mining, valued at live prices, with an **even or by-contribution split**. |
| **Appraise & Split** | Paste a pile of ore for the total ISK and a fair per-member split. No login needed. |

## Screenshots

**Refine.** An instant sell-raw or reprocess verdict with the full mineral breakdown.

![Refine](screenshots/refine.png)

**Mining Ledger.** Log in with EVE and split the fleet's mining fairly.

## Install and run from source

**You need [Python 3.10+](https://www.python.org/downloads/)** (tick *Add Python to PATH* during install).

1. **Download** this project (green **Code > Download ZIP**, then unzip) or `git clone` it.
2. Open a terminal in the folder and install the two dependencies:
   ```
   pip install -r requirements.txt
   ```
3. **Start it:**
   - Windows: double-click **`run_eve_foreman.bat`**
   - Any OS: `python app.py`
4. Your browser opens **http://localhost:8088**.

## Connect your EVE account (for the Mining Ledger tab)

The first four tabs work with no login. The **Mining Ledger** needs a free, one-time connection so EVE will let Foreman read *your* mining data.

You log in on **CCP's own page**. Foreman never sees your password, only a token you can revoke any time. It uses **PKCE**, so there is no secret to manage.

**If this build came with a Client ID bundled** (the .exe does): open the **Mining Ledger** tab and click **Log in with EVE Online**. Done.

**Otherwise, register your own free app once (about 3 minutes):**
1. Go to **https://developers.eveonline.com**, log in, then **Manage Applications > Create New Application**.
2. **Name:** anything (e.g. `My Fleet Foreman`). **Description:** anything.
3. **Callback URL:** `http://localhost:8088/callback` *(exact)*
4. **Scopes:** add **`esi-industry.read_character_mining.v1`** (and `esi-industry.read_corporation_mining.v1` for corp mode later).
5. **Create**, then copy the **Client ID** (ignore the Secret, it is not needed).
6. In Foreman, **Mining Ledger** tab, **First-time setup**: paste the Client ID and **Save**.

Then: **Log in with EVE Online**, **Authorize**, **Pull mining data**.

> **Heads-up:** CCP's Mining Ledger updates only about **once a day** and covers only the last ~30 days. If it comes back empty, you haven't mined recently; it is not a bug. Use **Load sample data** to see the layout.

## How to use each tab

- **What to Mine:** open the **reprocessing setup** bar and set your base station yield % and skills once. The table then shows the best ore *for you*, comparing selling raw against reprocessing. Higher "Best ISK/m³" means more value per cargo trip.
- **Fleet Yield:** type how many of each ship are in the fleet. The defaults are mid-skill ballparks; tune the yield and hold numbers to your fit. Tick **Fleet boost** if an Orca/Porpoise is running mining bursts.
- **Refine:** pick an ore and a quantity to see how much ISK you'd get selling it raw against reprocessing it into minerals at your efficiency.
- **Mining Ledger:** after login, **Pull mining data**. Add as many characters as you like (log in again for each). The split shows both an even split and each pilot's own contribution.
- **Appraise & Split:** paste lines like `Veldspar 250000`. Choose buy or sell value and how many fleet members to split between.

## Privacy and safety

- Foreman runs **entirely on your computer**. Nothing is sent anywhere except read requests to CCP's official API and public market data.
- Your login token is stored locally in `tokens.json` (git-ignored, never shared).
- The access is **read-only**. Foreman cannot undock, trade, or change anything in game. Revoke access any time at <https://community.eveonline.com/support/third-party-applications/>.

## Bugs and ideas

This is an early free release, so **please open a GitHub Issue**. Tell me what you did, what you expected, and what happened (paste any error text). Mining-fleet feedback especially welcome.

## Roadmap

- A proper Windows installer (today it is a single .exe)
- **Deluxe version:** an always-on-top **mining HUD overlay**, corp/structure ledger mode, profit history graphs, price alerts, ice and moon ore, and compression math.

## Who built it

EVE Fleet Foreman is built and maintained by **[Honey Badger Software](https://honeybadger.software)**, a one-person studio that also makes the War Room and Bounty Board for EVE Frontier, a modded Rust server and Battle Aura for WoW Forever. More projects and contact: **[honeybadger.software](https://honeybadger.software)**. Got an idea, a bug, or want something custom built? Reach out through the site or open an Issue here.

If Foreman saves your fleet some time, a star on the repo and a share with your corp really helps.

## Credits and legal

- Ore/type data and Mining Ledger: **CCP ESI** (`esi.evetech.net`)
- Market prices: **Fuzzwork** (`market.fuzzwork.co.uk`)

> EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights reserved worldwide. This is an unofficial, fan-made tool and is **not affiliated with or endorsed by CCP hf.** All EVE-related materials are property of CCP hf.

Released under the **MIT License**, see [LICENSE](LICENSE).
