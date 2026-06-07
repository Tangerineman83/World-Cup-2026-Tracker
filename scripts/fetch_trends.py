#!/usr/bin/env python3
"""
fetch_trends.py  —  Wikipedia + Wikivoyage Uplift Tracker (Last Week only)

Fetches rolling last-7-days Wikipedia pageviews for all 16 World Cup host cities.
Compares against same 7-day window averaged across 2019, 2022, 2023 (clean baseline years).

Combined uplift = (stadium_wikipedia * 0.50) + (wikivoyage * 0.50)
Stadium floored at 1.0x to prevent transient fetch failures collapsing rankings.
Wikivoyage clamped to [1.0x, 10.0x] to smooth noise from smaller sample sizes.

Weekly discrete periods (W1-W4) removed until tournament begins.
"""

import json, time, os, subprocess, urllib.request, urllib.error
from datetime import datetime, timezone, date, timedelta

CITIES = [
    {"name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",
     "stadium": "MetLife Stadium",        "stadium_article": "MetLife_Stadium",
     "city_article": "New_York_City",     "wikivoyage_article": "New_York_City",
     "wikiUrl": "https://en.wikipedia.org/wiki/MetLife_Stadium"},
    {"name": "Los Angeles",           "country": "USA", "flag": "US", "region": "West",
     "stadium": "SoFi Stadium",           "stadium_article": "SoFi_Stadium",
     "city_article": "Los_Angeles",       "wikivoyage_article": "Los_Angeles",
     "wikiUrl": "https://en.wikipedia.org/wiki/SoFi_Stadium"},
    {"name": "Dallas",                "country": "USA", "flag": "US", "region": "Central",
     "stadium": "AT&T Stadium",           "stadium_article": "AT%26T_Stadium",
     "city_article": "Dallas",            "wikivoyage_article": "Dallas",
     "wikiUrl": "https://en.wikipedia.org/wiki/AT%26T_Stadium"},
    {"name": "Mexico City",           "country": "MEX", "flag": "MX", "region": "Central",
     "stadium": "Estadio Azteca",         "stadium_article": "Estadio_Azteca",
     "city_article": "Mexico_City",       "wikivoyage_article": "Mexico_City",
     "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Azteca"},
    {"name": "Miami",                 "country": "USA", "flag": "US", "region": "East",
     "stadium": "Hard Rock Stadium",      "stadium_article": "Hard_Rock_Stadium",
     "city_article": "Miami",             "wikivoyage_article": "Miami",
     "wikiUrl": "https://en.wikipedia.org/wiki/Hard_Rock_Stadium"},
    {"name": "Atlanta",               "country": "USA", "flag": "US", "region": "Central",
     "stadium": "Mercedes-Benz Stadium",  "stadium_article": "Mercedes-Benz_Stadium",
     "city_article": "Atlanta",           "wikivoyage_article": "Atlanta",
     "wikiUrl": "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium"},
    {"name": "San Francisco",         "country": "USA", "flag": "US", "region": "West",
     "stadium": "Levi's Stadium",         "stadium_article": "Levi%27s_Stadium",
     "city_article": "San_Francisco",     "wikivoyage_article": "San_Francisco",
     "wikiUrl": "https://en.wikipedia.org/wiki/Levi%27s_Stadium"},
    {"name": "Seattle",               "country": "USA", "flag": "US", "region": "West",
     "stadium": "Lumen Field",            "stadium_article": "Lumen_Field",
     "city_article": "Seattle",           "wikivoyage_article": "Seattle",
     "wikiUrl": "https://en.wikipedia.org/wiki/Lumen_Field"},
    {"name": "Toronto",               "country": "CAN", "flag": "CA", "region": "East",
     "stadium": "BMO Field",              "stadium_article": "BMO_Field",
     "city_article": "Toronto",           "wikivoyage_article": "Toronto",
     "wikiUrl": "https://en.wikipedia.org/wiki/BMO_Field"},
    {"name": "Boston",                "country": "USA", "flag": "US", "region": "East",
     "stadium": "Gillette Stadium",       "stadium_article": "Gillette_Stadium",
     "city_article": "Boston",            "wikivoyage_article": "Boston",
     "wikiUrl": "https://en.wikipedia.org/wiki/Gillette_Stadium"},
    {"name": "Guadalajara",           "country": "MEX", "flag": "MX", "region": "West",
     "stadium": "Estadio Akron",          "stadium_article": "Estadio_Akron",
     "city_article": "Guadalajara",       "wikivoyage_article": "Guadalajara",
     "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Akron"},
    {"name": "Houston",               "country": "USA", "flag": "US", "region": "Central",
     "stadium": "NRG Stadium",            "stadium_article": "NRG_Stadium",
     "city_article": "Houston",           "wikivoyage_article": "Houston",
     "wikiUrl": "https://en.wikipedia.org/wiki/NRG_Stadium"},
    {"name": "Philadelphia",          "country": "USA", "flag": "US", "region": "East",
     "stadium": "Lincoln Financial Field","stadium_article": "Lincoln_Financial_Field",
     "city_article": "Philadelphia",      "wikivoyage_article": "Philadelphia",
     "wikiUrl": "https://en.wikipedia.org/wiki/Lincoln_Financial_Field"},
    {"name": "Vancouver",             "country": "CAN", "flag": "CA", "region": "West",
     "stadium": "BC Place",               "stadium_article": "BC_Place",
     "city_article": "Vancouver",         "wikivoyage_article": "Vancouver",
     "wikiUrl": "https://en.wikipedia.org/wiki/BC_Place"},
    {"name": "Monterrey",             "country": "MEX", "flag": "MX", "region": "Central",
     "stadium": "Estadio BBVA",           "stadium_article": "Estadio_BBVA",
     "city_article": "Monterrey",         "wikivoyage_article": "Monterrey",
     "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_BBVA"},
    {"name": "Kansas City",           "country": "USA", "flag": "US", "region": "Central",
     "stadium": "Arrowhead Stadium",      "stadium_article": "Arrowhead_Stadium",
     "city_article": "Kansas_City,_Missouri", "wikivoyage_article": "Kansas_City",
     "wikiUrl": "https://en.wikipedia.org/wiki/Arrowhead_Stadium"},
]

# Clean baseline years — no Copa America, Club WC, or COVID in Jun-Jul window
BASELINE_YEARS       = [2019, 2022, 2023]
BASELINE_DESCRIPTION = "Same 7-day window averaged across 2019, 2022, 2023"

# Weights: 50% stadium + 50% Wikivoyage (city Wikipedia removed)
STADIUM_WEIGHT    = 0.50
WIKIVOYAGE_WEIGHT = 0.50

# Wikivoyage noise controls
WIKIVOYAGE_FLOOR    = 100.0   # 1.0x minimum
WIKIVOYAGE_CAP      = 1000.0  # 10.0x maximum
WIKIVOYAGE_LOW_CONF = 150     # avg views/week below this = flag as low confidence

WIKI_AGENT = "WC2026UpliftTracker/1.0 (public research; github.com/tracker)"

# Full 2026 World Cup schedule — free public domain JSON, no API key required
# Source: https://github.com/openfootball/worldcup.json
SCHEDULE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# Maps ground strings in the schedule JSON to our 16 city names
GROUND_MAP = {
    "Mexico City":                           "Mexico City",
    "Guadalajara (Zapopan)":                "Guadalajara",
    "Monterrey (Guadalupe)":                "Monterrey",
    "Atlanta":                              "Atlanta",
    "Boston (Foxborough)":                  "Boston",
    "Dallas (Arlington)":                   "Dallas",
    "Houston":                              "Houston",
    "Kansas City":                          "Kansas City",
    "Los Angeles (Inglewood)":              "Los Angeles",
    "Miami (Miami Gardens)":               "Miami",
    "New York/New Jersey (East Rutherford)":"New York / New Jersey",
    "Philadelphia":                         "Philadelphia",
    "San Francisco Bay Area (Santa Clara)": "San Francisco",
    "Seattle":                              "Seattle",
    "Toronto":                              "Toronto",
    "Vancouver":                            "Vancouver",
}

GROUP_ROUNDS    = {"Matchday " + str(i) for i in range(1, 18)}
KNOCKOUT_ROUNDS = {"Round of 32", "Round of 16", "Quarter-final",
                   "Semi-final", "Match for third place", "Final"}


# ── API ────────────────────────────────────────────────────────────────────────

def get_pageviews(project, article, start_date, end_date, retries=4):
    start = start_date.replace("-", "")
    end   = end_date.replace("-", "")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           + project + "/all-access/all-agents/"
           + article + "/daily/" + start + "/" + end)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": WIKI_AGENT})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                return sum(item["views"] for item in data.get("items", []))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (2 ** attempt)
                print("    429 rate limit - waiting " + str(wait) + "s...")
                time.sleep(wait)
            elif e.code == 404:
                print("    404 not found: " + article)
                return 0
            else:
                print("    HTTP " + str(e.code) + ": " + article)
                return 0
        except Exception as e:
            print("    Error (" + article + "): " + str(e))
            return 0
    print("    All retries failed: " + article)
    return 0

def wiki(article, start, end):
    return get_pageviews("en.wikipedia", article, start, end)

def voyage(article, start, end):
    return get_pageviews("en.wikivoyage", article, start, end)


# ── Uplift ─────────────────────────────────────────────────────────────────────

def uplift(views, avg_weekly, week_fraction=1.0):
    if avg_weekly <= 0:
        return 0.0
    return round((views / week_fraction) / avg_weekly * 100, 1)

def clamp_wikivoyage(raw, low_conf=False):
    cap = 500.0 if low_conf else WIKIVOYAGE_CAP
    return round(max(WIKIVOYAGE_FLOOR, min(cap, raw)), 1)

def combined(su, vu):
    """50% stadium (floored at 1.0x) + 50% Wikivoyage."""
    su_floored = max(100.0, su)  # 1.0x floor — fetch failures never collapse ranking
    return round(su_floored * STADIUM_WEIGHT + vu * WIKIVOYAGE_WEIGHT, 1)

def to_points(scores):
    if not scores or max(scores.values()) == 0:
        return {n: 0 for n in scores}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {name: max(0, 10 - i) for i, (name, _) in enumerate(ranked)}


# ── Git helper ─────────────────────────────────────────────────────────────────

def git_commit(message):
    """Commit and push data.json. Non-fatal if git not configured."""
    try:
        subprocess.run(["git", "add", "data/data.json"], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode != 0:  # there are changes to commit
            subprocess.run(["git", "commit", "-m", message], check=True)
            subprocess.run(["git", "push"], check=True)
            print("    Committed: " + message)
        else:
            print("    No changes to commit.")
    except subprocess.CalledProcessError as e:
        print("    Git commit failed (non-fatal): " + str(e))


# ── Baseline ───────────────────────────────────────────────────────────────────

def fetch_match_counts():
    """
    Fetch the 2026 World Cup schedule from openfootball (public domain, no API key)
    and return match counts per city split by group stage and knockout.
    Falls back to hardcoded totals if the fetch fails.
    """
    # Hardcoded fallback (correct as of schedule published June 2026)
    fallback = {
        "New York / New Jersey": {"group": 5, "knockout": 3, "total": 8},
        "Los Angeles":           {"group": 5, "knockout": 3, "total": 8},
        "Dallas":                {"group": 5, "knockout": 4, "total": 9},
        "Mexico City":           {"group": 3, "knockout": 2, "total": 5},
        "Miami":                 {"group": 4, "knockout": 3, "total": 7},
        "Atlanta":               {"group": 5, "knockout": 3, "total": 8},
        "San Francisco":         {"group": 5, "knockout": 1, "total": 6},
        "Seattle":               {"group": 4, "knockout": 2, "total": 6},
        "Toronto":               {"group": 5, "knockout": 1, "total": 6},
        "Boston":                {"group": 5, "knockout": 2, "total": 7},
        "Guadalajara":           {"group": 4, "knockout": 0, "total": 4},
        "Houston":               {"group": 5, "knockout": 2, "total": 7},
        "Philadelphia":          {"group": 5, "knockout": 1, "total": 6},
        "Vancouver":             {"group": 5, "knockout": 2, "total": 7},
        "Monterrey":             {"group": 3, "knockout": 1, "total": 4},
        "Kansas City":           {"group": 4, "knockout": 2, "total": 6},
    }
    try:
        req = urllib.request.Request(SCHEDULE_URL, headers={"User-Agent": WIKI_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        matches = data.get("matches", [])
        counts  = {city: {"group": 0, "knockout": 0, "total": 0, "played": 0}
                   for city in GROUND_MAP.values()}
        today_str = date.today().strftime("%Y-%m-%d")
        for m in matches:
            city = GROUND_MAP.get(m.get("ground", ""))
            if not city:
                continue
            rnd = m.get("round", "")
            if rnd in GROUP_ROUNDS:
                counts[city]["group"]    += 1
            elif rnd in KNOCKOUT_ROUNDS:
                counts[city]["knockout"] += 1
            else:
                continue
            counts[city]["total"] += 1
            # Count played matches (score present or date has passed)
            if m.get("date", "9999") <= today_str:
                score1 = m.get("score1")
                score2 = m.get("score2")
                if score1 is not None and score2 is not None:
                    counts[city]["played"] += 1
        print("  Schedule fetched: " + str(sum(c["total"] for c in counts.values())) + " matches mapped")
        return counts
    except Exception as e:
        print("  Schedule fetch failed (" + str(e) + ") - using hardcoded fallback")
        return {k: dict(v, played=0) for k, v in fallback.items()}


def baseline_dates(start_date, end_date, year):
    """Return equivalent window in a prior year (same calendar dates)."""
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    return s.replace(year=year).strftime("%Y-%m-%d"), e.replace(year=year).strftime("%Y-%m-%d")

def fetch_baselines(l7_start, l7_end, existing_baselines):
    """
    Fetch same-period baseline for the last-7-days window across BASELINE_YEARS.
    Saves and commits after each city so progress is never lost.
    Resumes from partial progress if a prior run was interrupted.
    """
    days = (date.fromisoformat(l7_end) - date.fromisoformat(l7_start)).days + 1
    wf   = days / 7.0
    n_years = len(BASELINE_YEARS)

    print("\n=== Fetching baselines (" + l7_start + " to " + l7_end + " in " + str(BASELINE_YEARS) + ") ===")

    baselines = existing_baselines.copy() if existing_baselines else {}
    already_done = set(baselines.keys())
    if already_done:
        print("  Resuming: " + str(len(already_done)) + "/16 cities already done")

    for i, city in enumerate(CITIES):
        n = city["name"]
        if n in already_done:
            print("  [" + str(i+1) + "/16] Skipping " + n + " (cached)")
            continue

        print("  [" + str(i+1) + "/16] " + n)
        s_total = c_total = v_total = 0

        for year in BASELINE_YEARS:
            bs, be = baseline_dates(l7_start, l7_end, year)
            sv = wiki(city["stadium_article"],       bs, be); time.sleep(1.0)
            vv = voyage(city["wikivoyage_article"],  bs, be); time.sleep(1.0)
            s_total += sv; v_total += vv

        s_avg = round((s_total / n_years) / wf, 1)
        v_avg = round((v_total / n_years) / wf, 1)
        v_low = v_avg < WIKIVOYAGE_LOW_CONF

        baselines[n] = {
            "stadium_avg_weekly":    s_avg,
            "wikivoyage_avg_weekly": v_avg,
            "stadium_total":         s_total,
            "wikivoyage_total":      v_total,
            "wikivoyage_low_conf":   v_low,
        }
        print("    stadium=" + str(s_avg) + "/wk  voyage=" + str(v_avg) +
              "/wk" + (" [LOW CONF]" if v_low else ""))

        # Save and commit after every city
        save_baselines_progress(baselines, l7_start, l7_end)
        git_commit("chore: baseline progress (" + str(len(baselines)) + "/16 cities)")

    return baselines

def save_baselines_progress(baselines, l7_start, l7_end):
    """Write baselines to data.json immediately (preserves any existing city data)."""
    os.makedirs("data", exist_ok=True)
    existing = {}
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["baselines"]           = baselines
    existing["baselineWindow"]      = l7_start + " to " + l7_end + " (equiv. in " + str(BASELINE_YEARS) + ")"
    existing["_baselineInProgress"] = True
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def load_baselines(existing_data, l7_start, l7_end):
    """
    Load cached baselines from data.json if they cover the same window.
    Returns (baselines_dict_or_None, is_complete).
    """
    if not existing_data:
        return None, False

    bl = existing_data.get("baselines", {})
    cached_window = existing_data.get("baselineWindow", "")
    in_progress   = existing_data.get("_baselineInProgress", False)
    expected_window = l7_start + " to " + l7_end + " (equiv. in " + str(BASELINE_YEARS) + ")"

    if not bl:
        print("  No baselines in data.json - fetching fresh.")
        return None, False

    if cached_window != expected_window:
        print("  Baseline window changed (" + cached_window + ") - fetching fresh.")
        return None, False

    if in_progress:
        n_done = len(bl)
        print("  Partial baselines found (" + str(n_done) + "/16) - will resume.")
        return bl, False

    if len(bl) < len(CITIES):
        print("  Incomplete baselines (" + str(len(bl)) + "/16) - will resume.")
        return bl, False

    print("  Baselines complete and current - reusing.")
    return bl, True


# ── Current week fetch ─────────────────────────────────────────────────────────

def fetch_article_with_zero_retry(fetch_fn, article, start, end, label, baseline_avg):
    """
    Fetch an article with an extra retry if zero views are returned
    but a non-zero baseline exists (indicates a transient 429, not genuine zero traffic).
    """
    views = fetch_fn(article, start, end)
    time.sleep(1.5)
    if views == 0 and baseline_avg > 0:
        print("    Zero views for " + label + " (baseline=" + str(baseline_avg) +
              "/wk) — retrying in 20s...")
        time.sleep(20)
        views = fetch_fn(article, start, end)
        time.sleep(1.5)
        if views == 0:
            print("    Still zero after retry — applying 1.0x floor")
        else:
            print("    Retry succeeded: " + str(views) + " views")
    return views


def fetch_current_week(l7_start, l7_end, baselines):
    """
    Fetch last-7-days views for stadium + Wikivoyage only (city Wikipedia removed).
    Applies a 1.0x floor to stadium uplift to prevent transient fetch failures
    from collapsing a city's ranking. Retries zero returns once before flooring.
    """
    days = (date.fromisoformat(l7_end) - date.fromisoformat(l7_start)).days + 1
    wf   = days / 7.0

    print("\n=== Fetching last 7 days (" + l7_start + " to " + l7_end + ") ===")
    print("    Signals: stadium Wikipedia (50%) + Wikivoyage (50%)")

    stadium_u = {}; voyage_u = {}; combined_u = {}

    for city in CITIES:
        n  = city["name"]
        bl = baselines.get(n, {})
        s_base = bl.get("stadium_avg_weekly", 0)
        v_base = bl.get("wikivoyage_avg_weekly", 0)

        # Stadium — with zero-retry
        sv = fetch_article_with_zero_retry(
            wiki, city["stadium_article"], l7_start, l7_end, n + " stadium", s_base)

        # Wikivoyage — with zero-retry
        vv = fetch_article_with_zero_retry(
            voyage, city["wikivoyage_article"], l7_start, l7_end, n + " wikivoyage", v_base)

        su     = uplift(sv, s_base, wf)
        vu_raw = uplift(vv, v_base, wf)
        vu     = clamp_wikivoyage(vu_raw, bl.get("wikivoyage_low_conf", False))
        wu     = combined(su, vu)  # stadium floor applied inside combined()

        stadium_u[n]  = su
        voyage_u[n]   = vu
        combined_u[n] = wu

        su_display = max(100.0, su)  # show floored value in logs
        print("  " + n.ljust(25) +
              " stadium=" + str(round(su_display/100, 2)) + "x" +
              ("(floored)" if su < 100 else "") +
              "  voyage=" + str(round(vu/100, 2)) + "x" +
              "  combined=" + str(round(wu/100, 2)) + "x")

    pts = to_points(combined_u)
    return {"stadium": stadium_u, "voyage": voyage_u, "combined": combined_u, "points": pts}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Wikipedia + Wikivoyage Uplift Tracker — Last 7 Days")
    print("Weights: stadium=50%  wikivoyage=50%  (city Wikipedia removed)")
    print("Baseline: same window in " + str(BASELINE_YEARS))

    today    = date.today()
    l7_end   = today.strftime("%Y-%m-%d")
    l7_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")

    # Load existing data
    existing_data = None
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    # Baselines: reuse if current, otherwise fetch (with per-city saves)
    cached_bl, is_complete = load_baselines(existing_data, l7_start, l7_end)

    if is_complete:
        baselines = cached_bl
    else:
        baselines = fetch_baselines(l7_start, l7_end, cached_bl or {})

    # Fetch match schedule counts
    print("\nFetching match schedule from openfootball...")
    match_counts = fetch_match_counts()

    # Fetch current week
    current = fetch_current_week(l7_start, l7_end, baselines)

    # Build results
    results = []
    for city in CITIES:
        n  = city["name"]
        bl = baselines.get(n, {})
        mc = match_counts.get(n, {"group": 0, "knockout": 0, "total": 0, "played": 0})
        results.append({
            "name":    n, "country": city["country"],
            "flag":    city["flag"], "region":  city["region"],
            "stadium": city["stadium"], "wikiUrl": city["wikiUrl"],
            "baselineStadiumAvgWeekly":  bl.get("stadium_avg_weekly",    0),
            "baselineVoyageAvgWeekly":   bl.get("wikivoyage_avg_weekly", 0),
            "wikivoyageLowConf":         bl.get("wikivoyage_low_conf",   False),
            "lastWeekCombined":  current["combined"][n],
            "lastWeekStadium":   current["stadium"][n],
            "lastWeekVoyage":    current["voyage"][n],
            "lastWeekPts":       current["points"][n],
            "matchesGroup":      mc["group"],
            "matchesKnockout":   mc["knockout"],
            "matchesTotal":      mc["total"],
            "matchesPlayed":     mc["played"],
        })

    results.sort(key=lambda x: x["lastWeekCombined"], reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25)
              + "  combined=" + str(city["lastWeekCombined"]) + "x"
              + "  pts=" + str(city["lastWeekPts"]))

    now = datetime.now(timezone.utc)
    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":          now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay":   now.strftime("%d %b %Y, %H:%Mz"),
            "metric":           "50% stadium Wikipedia + 50% Wikivoyage vs same-period baseline (2019/2022/2023) | Match counts from openfootball/worldcup.json",
            "baselineYears":    BASELINE_YEARS,
            "baselineWindow":   l7_start + " to " + l7_end + " (equiv. in " + str(BASELINE_YEARS) + ")",
            "baselines":        baselines,
            "cities":           results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Top city: " + results[0]["name"]
          + " (" + str(results[0]["lastWeekCombined"]) + "x)")


main()
