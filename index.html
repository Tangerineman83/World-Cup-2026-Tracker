#!/usr/bin/env python3
"""
fetch_trends.py  —  Wikipedia + Wikivoyage Uplift Tracker

Combined uplift index vs 12-month baseline:
  combined = (stadium_wikipedia * 0.50) + (wikivoyage_city * 0.30) + (city_wikipedia * 0.20)

Wikivoyage uplift is clamped to [1.0x, 10.0x] to smooth noise from small sample sizes.
Stadium and city Wikipedia are uncapped (large baselines, noise-resistant).

Low-confidence flag: Wikivoyage baseline < 150 views/week -> flagged in output.
"""

import json, time, os, urllib.request, urllib.error
from datetime import datetime, timezone, date, timedelta

CITIES = [
    {
        "name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",
        "stadium": "MetLife Stadium",
        "stadium_article":    "MetLife_Stadium",
        "city_article":       "New_York_City",
        "wikivoyage_article": "New_York_City",
        "wikiUrl": "https://en.wikipedia.org/wiki/MetLife_Stadium",
    },
    {
        "name": "Los Angeles", "country": "USA", "flag": "US", "region": "West",
        "stadium": "SoFi Stadium",
        "stadium_article":    "SoFi_Stadium",
        "city_article":       "Los_Angeles",
        "wikivoyage_article": "Los_Angeles",
        "wikiUrl": "https://en.wikipedia.org/wiki/SoFi_Stadium",
    },
    {
        "name": "Dallas", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "AT&T Stadium",
        "stadium_article":    "AT%26T_Stadium",
        "city_article":       "Dallas",
        "wikivoyage_article": "Dallas",
        "wikiUrl": "https://en.wikipedia.org/wiki/AT%26T_Stadium",
    },
    {
        "name": "Mexico City", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium": "Estadio Azteca",
        "stadium_article":    "Estadio_Azteca",
        "city_article":       "Mexico_City",
        "wikivoyage_article": "Mexico_City",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Azteca",
    },
    {
        "name": "Miami", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Hard Rock Stadium",
        "stadium_article":    "Hard_Rock_Stadium",
        "city_article":       "Miami",
        "wikivoyage_article": "Miami",
        "wikiUrl": "https://en.wikipedia.org/wiki/Hard_Rock_Stadium",
    },
    {
        "name": "Atlanta", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "Mercedes-Benz Stadium",
        "stadium_article":    "Mercedes-Benz_Stadium",
        "city_article":       "Atlanta",
        "wikivoyage_article": "Atlanta",
        "wikiUrl": "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium",
    },
    {
        "name": "San Francisco", "country": "USA", "flag": "US", "region": "West",
        "stadium": "Levi's Stadium",
        "stadium_article":    "Levi%27s_Stadium",
        "city_article":       "San_Francisco",
        "wikivoyage_article": "San_Francisco",
        "wikiUrl": "https://en.wikipedia.org/wiki/Levi%27s_Stadium",
    },
    {
        "name": "Seattle", "country": "USA", "flag": "US", "region": "West",
        "stadium": "Lumen Field",
        "stadium_article":    "Lumen_Field",
        "city_article":       "Seattle",
        "wikivoyage_article": "Seattle",
        "wikiUrl": "https://en.wikipedia.org/wiki/Lumen_Field",
    },
    {
        "name": "Toronto", "country": "CAN", "flag": "CA", "region": "East",
        "stadium": "BMO Field",
        "stadium_article":    "BMO_Field",
        "city_article":       "Toronto",
        "wikivoyage_article": "Toronto",
        "wikiUrl": "https://en.wikipedia.org/wiki/BMO_Field",
    },
    {
        "name": "Boston", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Gillette Stadium",
        "stadium_article":    "Gillette_Stadium",
        "city_article":       "Boston",
        "wikivoyage_article": "Boston",
        "wikiUrl": "https://en.wikipedia.org/wiki/Gillette_Stadium",
    },
    {
        "name": "Guadalajara", "country": "MEX", "flag": "MX", "region": "West",
        "stadium": "Estadio Akron",
        "stadium_article":    "Estadio_Akron",
        "city_article":       "Guadalajara",
        "wikivoyage_article": "Guadalajara",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Akron",
    },
    {
        "name": "Houston", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "NRG Stadium",
        "stadium_article":    "NRG_Stadium",
        "city_article":       "Houston",
        "wikivoyage_article": "Houston",
        "wikiUrl": "https://en.wikipedia.org/wiki/NRG_Stadium",
    },
    {
        "name": "Philadelphia", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Lincoln Financial Field",
        "stadium_article":    "Lincoln_Financial_Field",
        "city_article":       "Philadelphia",
        "wikivoyage_article": "Philadelphia",
        "wikiUrl": "https://en.wikipedia.org/wiki/Lincoln_Financial_Field",
    },
    {
        "name": "Vancouver", "country": "CAN", "flag": "CA", "region": "West",
        "stadium": "BC Place",
        "stadium_article":    "BC_Place",
        "city_article":       "Vancouver",
        "wikivoyage_article": "Vancouver",
        "wikiUrl": "https://en.wikipedia.org/wiki/BC_Place",
    },
    {
        "name": "Monterrey", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium": "Estadio BBVA",
        "stadium_article":    "Estadio_BBVA",
        "city_article":       "Monterrey",
        "wikivoyage_article": "Monterrey",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_BBVA",
    },
    {
        "name": "Kansas City", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "Arrowhead Stadium",
        "stadium_article":    "Arrowhead_Stadium",
        "city_article":       "Kansas_City,_Missouri",
        "wikivoyage_article": "Kansas_City",
        "wikiUrl": "https://en.wikipedia.org/wiki/Arrowhead_Stadium",
    },
]

WEEKS = [
    {"label": "Week 1", "start": "2026-06-11", "end": "2026-06-17"},
    {"label": "Week 2", "start": "2026-06-18", "end": "2026-06-24"},
    {"label": "Week 3", "start": "2026-06-25", "end": "2026-07-01"},
    {"label": "Week 4", "start": "2026-07-02", "end": "2026-07-08"},
]

BASELINE_START = "2025-06-01"
BASELINE_END   = "2026-05-31"
BASELINE_WEEKS = 52

# Weights
STADIUM_WEIGHT    = 0.50
WIKIVOYAGE_WEIGHT = 0.30
CITY_WIKI_WEIGHT  = 0.20

# Wikivoyage noise controls (as index values: 100 = 1x, 1000 = 10x)
WIKIVOYAGE_FLOOR      = 100.0   # 1.0x minimum — no downward drag from noise
WIKIVOYAGE_CAP        = 1000.0  # 10.0x maximum — prevents outlier spikes from tiny baselines
WIKIVOYAGE_LOW_CONF   = 150     # views/week below this flags low confidence

WIKI_AGENT = "WC2026UpliftTracker/1.0 (public research; github.com/tracker)"


# ── API ────────────────────────────────────────────────────────────────────────

def get_pageviews(project, article, start_date, end_date, retries=4):
    """
    Fetch total pageviews from Wikimedia for any project (wikipedia or wikivoyage).
    project: e.g. 'en.wikipedia' or 'en.wikivoyage'
    """
    start = start_date.replace("-", "")
    end   = end_date.replace("-", "")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        + project + "/all-access/all-agents/"
        + article + "/daily/" + start + "/" + end
    )
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
                print("    404 not found: " + project + "/" + article)
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
    """Shorthand for English Wikipedia."""
    return get_pageviews("en.wikipedia", article, start, end)


def voyage(article, start, end):
    """Shorthand for English Wikivoyage."""
    return get_pageviews("en.wikivoyage", article, start, end)


# ── Uplift calculation ─────────────────────────────────────────────────────────

def uplift(views, avg_weekly, week_fraction=1.0):
    """Raw uplift index. Returns 0.0 if baseline missing."""
    if avg_weekly <= 0:
        return 0.0
    weekly_equiv = views / week_fraction
    return round(weekly_equiv / avg_weekly * 100, 1)


def clamp_wikivoyage(raw_uplift, low_conf=False):
    """
    Apply floor and cap to Wikivoyage uplift.
    Floor: 100 (1.0x) — prevents noisy below-baseline weeks from dragging score down.
    Cap:  1000 (10.0x) — prevents outlier spikes on small samples inflating score.
    Low-confidence baseline (<150 views/week): cap reduced to 500 (5x) for extra caution.
    """
    effective_cap = 500.0 if low_conf else WIKIVOYAGE_CAP
    return round(max(WIKIVOYAGE_FLOOR, min(effective_cap, raw_uplift)), 1)


def combined(stadium_u, wikivoyage_u, city_u):
    """Weighted combination of three uplift signals."""
    return round(
        stadium_u    * STADIUM_WEIGHT +
        wikivoyage_u * WIKIVOYAGE_WEIGHT +
        city_u       * CITY_WIKI_WEIGHT,
        1
    )


def to_points(combined_scores):
    """1st=10pts ... 10th=1pt, 11th-16th=0pts. No points if all zero."""
    if not combined_scores or max(combined_scores.values()) == 0:
        return {n: 0 for n in combined_scores}
    ranked = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return {name: max(0, 10 - i) for i, (name, _) in enumerate(ranked)}


# ── Baseline ───────────────────────────────────────────────────────────────────

def fetch_baselines():
    """Full 12-month baseline fetch for all three signals."""
    print("\n=== Fetching 12-month baselines (" + BASELINE_START + " to " + BASELINE_END + ") ===")
    print("    (Stored in data.json and reused on future runs)")
    baselines = {}
    for city in CITIES:
        n = city["name"]
        print("  " + n)

        st = wiki(city["stadium_article"],    BASELINE_START, BASELINE_END)
        time.sleep(1.5)
        ct = wiki(city["city_article"],       BASELINE_START, BASELINE_END)
        time.sleep(1.5)
        vt = voyage(city["wikivoyage_article"], BASELINE_START, BASELINE_END)
        time.sleep(1.5)

        s_avg = round(st / BASELINE_WEEKS, 1)
        c_avg = round(ct / BASELINE_WEEKS, 1)
        v_avg = round(vt / BASELINE_WEEKS, 1)
        v_low = v_avg < WIKIVOYAGE_LOW_CONF

        baselines[n] = {
            "stadium_avg_weekly":    s_avg,
            "city_avg_weekly":       c_avg,
            "wikivoyage_avg_weekly": v_avg,
            "stadium_total":         st,
            "city_total":            ct,
            "wikivoyage_total":      vt,
            "wikivoyage_low_conf":   v_low,
        }
        print("    stadium=" + str(s_avg) + "/wk"
              + "  city=" + str(c_avg) + "/wk"
              + "  voyage=" + str(v_avg) + "/wk"
              + (" [LOW CONF]" if v_low else ""))
    return baselines


def load_baselines(existing_data):
    """
    Reuse baselines from data.json if valid.
    Returns (baselines_dict, needs_refetch_list).
    needs_refetch contains (name, kind) tuples for any zero baselines.
    """
    if not existing_data:
        return None, []
    cities = existing_data.get("cities", [])
    if not cities or "baselineStadiumAvgWeekly" not in cities[0]:
        return None, []

    result = {}
    needs_refetch = []
    for c in cities:
        n = c["name"]
        s = c.get("baselineStadiumAvgWeekly",    0)
        cv = c.get("baselineCityAvgWeekly",       0)
        v = c.get("baselineVoyageAvgWeekly",      0)
        result[n] = {
            "stadium_avg_weekly":    s,
            "city_avg_weekly":       cv,
            "wikivoyage_avg_weekly": v,
            "stadium_total":         c.get("baselineStadiumTotal",    0),
            "city_total":            c.get("baselineCityTotal",       0),
            "wikivoyage_total":      c.get("baselineVoyageTotal",     0),
            "wikivoyage_low_conf":   v < WIKIVOYAGE_LOW_CONF,
        }
        if s  == 0: needs_refetch.append((n, "stadium"))
        if cv == 0: needs_refetch.append((n, "city"))
        if v  == 0: needs_refetch.append((n, "wikivoyage"))

    if needs_refetch:
        print("  Zero baselines found - will re-fetch:")
        for name, kind in needs_refetch:
            print("    -> " + name + " (" + kind + ")")
    else:
        print("  All baselines valid - reusing.")
    return result, needs_refetch


def refetch_baselines(existing, needs_refetch):
    """Partial re-fetch: only articles with zero baselines."""
    print("\n=== Partial baseline re-fetch ===")
    baselines = dict(existing)
    for name, kind in needs_refetch:
        city = next(c for c in CITIES if c["name"] == name)
        print("  Re-fetching " + kind + " for: " + name)
        if kind == "stadium":
            t = wiki(city["stadium_article"], BASELINE_START, BASELINE_END)
            time.sleep(1.5)
            if t > 0:
                baselines[name]["stadium_avg_weekly"] = round(t / BASELINE_WEEKS, 1)
                baselines[name]["stadium_total"]      = t
                print("    -> " + str(baselines[name]["stadium_avg_weekly"]) + "/wk")
            else:
                print("    -> Still 0 - will retry next run")
        elif kind == "city":
            t = wiki(city["city_article"], BASELINE_START, BASELINE_END)
            time.sleep(1.5)
            if t > 0:
                baselines[name]["city_avg_weekly"] = round(t / BASELINE_WEEKS, 1)
                baselines[name]["city_total"]      = t
                print("    -> " + str(baselines[name]["city_avg_weekly"]) + "/wk")
            else:
                print("    -> Still 0 - will retry next run")
        elif kind == "wikivoyage":
            t = voyage(city["wikivoyage_article"], BASELINE_START, BASELINE_END)
            time.sleep(1.5)
            if t > 0:
                v_avg = round(t / BASELINE_WEEKS, 1)
                baselines[name]["wikivoyage_avg_weekly"] = v_avg
                baselines[name]["wikivoyage_total"]      = t
                baselines[name]["wikivoyage_low_conf"]   = v_avg < WIKIVOYAGE_LOW_CONF
                print("    -> " + str(v_avg) + "/wk"
                      + (" [LOW CONF]" if baselines[name]["wikivoyage_low_conf"] else ""))
            else:
                print("    -> Still 0 - will retry next run")
    return baselines


# ── Period fetch ───────────────────────────────────────────────────────────────

def fetch_period(label, start_date, end_date, baselines):
    """Fetch all three signals, compute uplifts and points for one time window."""
    days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    wf   = days / 7.0  # week fraction for normalisation
    print("\n  [" + label + "] " + start_date + " to " + end_date)

    stadium_u  = {}
    city_u     = {}
    voyage_u   = {}
    combined_u = {}

    for city in CITIES:
        n  = city["name"]
        bl = baselines[n]

        sv = wiki(city["stadium_article"],      start_date, end_date); time.sleep(1.5)
        cv = wiki(city["city_article"],          start_date, end_date); time.sleep(1.5)
        vv = voyage(city["wikivoyage_article"],  start_date, end_date); time.sleep(1.5)

        # Warn on zero views where baseline exists
        if sv == 0 and bl["stadium_avg_weekly"]    > 0: print("    WARNING: " + n + " stadium=0 (baseline=" + str(bl["stadium_avg_weekly"]) + ")")
        if cv == 0 and bl["city_avg_weekly"]        > 0: print("    WARNING: " + n + " city=0 (baseline=" + str(bl["city_avg_weekly"]) + ")")
        if vv == 0 and bl["wikivoyage_avg_weekly"]  > 0: print("    WARNING: " + n + " voyage=0 (baseline=" + str(bl["wikivoyage_avg_weekly"]) + ")")

        su = uplift(sv, bl["stadium_avg_weekly"],    wf)
        cu = uplift(cv, bl["city_avg_weekly"],       wf)
        vu_raw = uplift(vv, bl["wikivoyage_avg_weekly"], wf)
        vu = clamp_wikivoyage(vu_raw, bl["wikivoyage_low_conf"])

        wu = combined(su, vu, cu)

        stadium_u[n]  = su
        city_u[n]     = cu
        voyage_u[n]   = vu
        combined_u[n] = wu

        print("  " + n.ljust(25)
              + " stadium=" + str(su) + "x"
              + "  voyage=" + str(vu) + "x" + (" [clamped from " + str(vu_raw) + "]" if vu != vu_raw else "")
              + ("~" if bl["wikivoyage_low_conf"] else "")
              + "  city=" + str(cu) + "x"
              + "  combined=" + str(wu) + "x")

    pts = to_points(combined_u)
    top3 = sorted(combined_u.items(), key=lambda x: x[1], reverse=True)[:3]
    print("  Top 3: " + " | ".join(n + " (" + str(v) + "x)" for n, v in top3))
    return {"stadium": stadium_u, "city": city_u, "voyage": voyage_u,
            "combined": combined_u, "points": pts}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Wikipedia + Wikivoyage Uplift Tracker")
    print("Weights: stadium=50% | wikivoyage=30% | city_wiki=20%")
    print("Wikivoyage bounds: floor=1.0x  cap=10.0x (5x if low-confidence baseline)")

    today = date.today()

    # Load / build baselines
    existing_data = None
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    loaded, needs_refetch = load_baselines(existing_data)
    if loaded is None:
        baselines = fetch_baselines()
    elif needs_refetch:
        baselines = refetch_baselines(loaded, needs_refetch)
    else:
        baselines = loaded

    # Discrete weeks
    week_data = {}
    for week in WEEKS:
        if today < date.fromisoformat(week["start"]):
            print("\nSkipping " + week["label"] + " (starts " + week["start"] + ")")
            continue
        print("\n=== " + week["label"] + " ===")
        week_data[week["label"]] = fetch_period(
            week["label"], week["start"], week["end"], baselines)

    # Rolling last 7 days
    print("\n=== Last 7 Days (rolling) ===")
    l7_end   = today.strftime("%Y-%m-%d")
    l7_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    l7 = fetch_period("Last 7 days", l7_start, l7_end, baselines)

    # Build results
    results = []
    for city in CITIES:
        n  = city["name"]
        bl = baselines[n]

        week_pts     = {}
        week_combined = {}
        week_stadium = {}
        week_city    = {}
        week_voyage  = {}

        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                wd = week_data[lbl]
                week_pts[lbl]      = wd["points"][n]
                week_combined[lbl] = wd["combined"][n]
                week_stadium[lbl]  = wd["stadium"][n]
                week_city[lbl]     = wd["city"][n]
                week_voyage[lbl]   = wd["voyage"][n]
            else:
                week_pts[lbl] = week_combined[lbl] = week_stadium[lbl] = week_city[lbl] = week_voyage[lbl] = None

        # First 4 weeks total = sum of available discrete week points only
        first4_pts = sum(v for v in week_pts.values() if v is not None)

        results.append({
            "name":    n, "country": city["country"],
            "flag":    city["flag"], "region": city["region"],
            "stadium": city["stadium"], "wikiUrl": city["wikiUrl"],
            # Baselines
            "baselineStadiumAvgWeekly":  bl["stadium_avg_weekly"],
            "baselineCityAvgWeekly":     bl["city_avg_weekly"],
            "baselineVoyageAvgWeekly":   bl["wikivoyage_avg_weekly"],
            "baselineStadiumTotal":      bl["stadium_total"],
            "baselineCityTotal":         bl["city_total"],
            "baselineVoyageTotal":       bl["wikivoyage_total"],
            "wikivoyageLowConf":         bl["wikivoyage_low_conf"],
            # Last 7 days
            "lastWeekCombined":  l7["combined"][n],
            "lastWeekStadium":   l7["stadium"][n],
            "lastWeekCity":      l7["city"][n],
            "lastWeekVoyage":    l7["voyage"][n],
            "lastWeekPts":       l7["points"][n],
            # Discrete weeks
            "weekPoints":        week_pts,
            "weekCombined":      week_combined,
            "weekStadium":       week_stadium,
            "weekCity":          week_city,
            "weekVoyage":        week_voyage,
            # Aggregate
            "first4Pts":         first4_pts,
        })

    results.sort(key=lambda x: (x["first4Pts"], x["lastWeekCombined"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25)
              + "  combined=" + str(city["lastWeekCombined"]) + "x"
              + "  pts=" + str(city["lastWeekPts"])
              + "  first4=" + str(city["first4Pts"]))

    now = datetime.now(timezone.utc)
    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "metric":         "Uplift index: 50% stadium Wikipedia + 30% Wikivoyage + 20% city Wikipedia vs 12-month baseline",
            "weights":        {"stadium": "50%", "wikivoyage": "30%", "city_wikipedia": "20%"},
            "wikivoyageBounds": {"floor": "1.0x", "cap": "10.0x", "low_conf_cap": "5.0x", "low_conf_threshold_weekly": WIKIVOYAGE_LOW_CONF},
            "baselineWindow": BASELINE_START + " to " + BASELINE_END,
            "weeks":          WEEKS,
            "cities":         results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Top city: " + results[0]["name"]
          + " (combined: " + str(results[0]["lastWeekCombined"]) + "x)")


main()
