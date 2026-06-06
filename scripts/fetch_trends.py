#!/usr/bin/env python3
"""
fetch_trends.py  —  Wikipedia Pageviews Uplift Edition (2/3 stadium, 1/3 city)

Metric: Weighted uplift index vs 12-month baseline.
  combined_uplift = (stadium_uplift * 2/3) + (city_uplift * 1/3)

Stadium uplift (2/3): clean event-specific signal — spikes almost exclusively
  due to sports events, not general city noise.

City uplift (1/3): broader destination/economic interest signal — captures
  tourists, business interest, and wider attention to the host location.
  Included with lower weight because city articles carry more background noise
  (news events, politics, disasters unrelated to the World Cup).

Uplift index = (views_this_period / avg_weekly_views_last_12_months) * 100
  100 = normal baseline
  300 = 3x normal interest
  850 = 8.5x spike

Baseline window: Jun 2025 – May 2026 (52 weeks pre-tournament).
Stored in data.json on first run and reused each Saturday.
"""

import json
import time
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, date, timedelta

# ── City + Stadium article pairs ───────────────────────────────────────────────

CITIES = [
    {
        "name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",
        "stadium":          "MetLife Stadium",
        "stadium_article":  "MetLife_Stadium",
        "city_article":     "New_York_City",
        "wikiUrl":          "https://en.wikipedia.org/wiki/MetLife_Stadium",
    },
    {
        "name": "Los Angeles", "country": "USA", "flag": "US", "region": "West",
        "stadium":          "SoFi Stadium",
        "stadium_article":  "SoFi_Stadium",
        "city_article":     "Los_Angeles",
        "wikiUrl":          "https://en.wikipedia.org/wiki/SoFi_Stadium",
    },
    {
        "name": "Dallas", "country": "USA", "flag": "US", "region": "Central",
        "stadium":          "AT&T Stadium",
        "stadium_article":  "AT%26T_Stadium",
        "city_article":     "Dallas",
        "wikiUrl":          "https://en.wikipedia.org/wiki/AT%26T_Stadium",
    },
    {
        "name": "Mexico City", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium":          "Estadio Azteca",
        "stadium_article":  "Estadio_Azteca",
        "city_article":     "Mexico_City",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Estadio_Azteca",
    },
    {
        "name": "Miami", "country": "USA", "flag": "US", "region": "East",
        "stadium":          "Hard Rock Stadium",
        "stadium_article":  "Hard_Rock_Stadium",
        "city_article":     "Miami",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Hard_Rock_Stadium",
    },
    {
        "name": "Atlanta", "country": "USA", "flag": "US", "region": "Central",
        "stadium":          "Mercedes-Benz Stadium",
        "stadium_article":  "Mercedes-Benz_Stadium",
        "city_article":     "Atlanta",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium",
    },
    {
        "name": "San Francisco", "country": "USA", "flag": "US", "region": "West",
        "stadium":          "Levi's Stadium",
        "stadium_article":  "Levi%27s_Stadium",
        "city_article":     "San_Francisco",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Levi%27s_Stadium",
    },
    {
        "name": "Seattle", "country": "USA", "flag": "US", "region": "West",
        "stadium":          "Lumen Field",
        "stadium_article":  "Lumen_Field",
        "city_article":     "Seattle",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Lumen_Field",
    },
    {
        "name": "Toronto", "country": "CAN", "flag": "CA", "region": "East",
        "stadium":          "BMO Field",
        "stadium_article":  "BMO_Field",
        "city_article":     "Toronto",
        "wikiUrl":          "https://en.wikipedia.org/wiki/BMO_Field",
    },
    {
        "name": "Boston", "country": "USA", "flag": "US", "region": "East",
        "stadium":          "Gillette Stadium",
        "stadium_article":  "Gillette_Stadium",
        "city_article":     "Boston",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Gillette_Stadium",
    },
    {
        "name": "Guadalajara", "country": "MEX", "flag": "MX", "region": "West",
        "stadium":          "Estadio Akron",
        "stadium_article":  "Estadio_Akron",
        "city_article":     "Guadalajara",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Estadio_Akron",
    },
    {
        "name": "Houston", "country": "USA", "flag": "US", "region": "Central",
        "stadium":          "NRG Stadium",
        "stadium_article":  "NRG_Stadium",
        "city_article":     "Houston",
        "wikiUrl":          "https://en.wikipedia.org/wiki/NRG_Stadium",
    },
    {
        "name": "Philadelphia", "country": "USA", "flag": "US", "region": "East",
        "stadium":          "Lincoln Financial Field",
        "stadium_article":  "Lincoln_Financial_Field",
        "city_article":     "Philadelphia",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Lincoln_Financial_Field",
    },
    {
        "name": "Vancouver", "country": "CAN", "flag": "CA", "region": "West",
        "stadium":          "BC Place",
        "stadium_article":  "BC_Place",
        "city_article":     "Vancouver",
        "wikiUrl":          "https://en.wikipedia.org/wiki/BC_Place",
    },
    {
        "name": "Monterrey", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium":          "Estadio BBVA",
        "stadium_article":  "Estadio_BBVA",
        "city_article":     "Monterrey",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Estadio_BBVA",
    },
    {
        "name": "Kansas City", "country": "USA", "flag": "US", "region": "Central",
        "stadium":          "Arrowhead Stadium",
        "stadium_article":  "Arrowhead_Stadium",
        "city_article":     "Kansas_City,_Missouri",
        "wikiUrl":          "https://en.wikipedia.org/wiki/Arrowhead_Stadium",
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

# Weighting: stadium is the cleaner event signal, city adds destination interest
STADIUM_WEIGHT = 2/3
CITY_WEIGHT    = 1/3

WIKI_AGENT = "WC2026UpliftTracker/1.0 (public research; github.com/tracker)"


# ── API ────────────────────────────────────────────────────────────────────────

def get_pageviews(article, start_date, end_date, retries=4):
    """Fetch total pageviews for a Wikipedia article over a date range."""
    start = start_date.replace("-", "")
    end   = end_date.replace("-", "")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/all-agents/" + article +
        "/daily/" + start + "/" + end
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


# ── Baseline ───────────────────────────────────────────────────────────────────

def fetch_baselines(existing=None, needs_refetch=None):
    """
    Fetch 12-month baselines for stadium and city articles.
    If existing baselines are provided, only re-fetches articles flagged as zero.
    Full fetch on first run; partial re-fetch on subsequent runs with failures.
    """
    if existing and needs_refetch:
        print("\n=== Partial baseline re-fetch (fixing zero baselines) ===")
        baselines = dict(existing)
        for name, kind in needs_refetch:
            city = next(c for c in CITIES if c["name"] == name)
            print("  Re-fetching " + kind + " baseline for: " + name)
            if kind == "stadium":
                total = get_pageviews(city["stadium_article"], BASELINE_START, BASELINE_END)
                time.sleep(1.5)
                if total > 0:
                    baselines[name]["stadium_avg_weekly"] = round(total / BASELINE_WEEKS, 1)
                    baselines[name]["stadium_total"]      = total
                    print("    -> " + str(baselines[name]["stadium_avg_weekly"]) + "/wk")
                else:
                    print("    -> Still returning 0 - will retry next run")
            elif kind == "city":
                total = get_pageviews(city["city_article"], BASELINE_START, BASELINE_END)
                time.sleep(1.5)
                if total > 0:
                    baselines[name]["city_avg_weekly"] = round(total / BASELINE_WEEKS, 1)
                    baselines[name]["city_total"]      = total
                    print("    -> " + str(baselines[name]["city_avg_weekly"]) + "/wk")
                else:
                    print("    -> Still returning 0 - will retry next run")
        return baselines

    print("\n=== Fetching 12-month baselines (Jun 2025 - May 2026) ===")
    print("    (Stored in data.json and reused on future runs)")
    baselines = {}
    for city in CITIES:
        print("  " + city["name"])
        stadium_total = get_pageviews(city["stadium_article"], BASELINE_START, BASELINE_END)
        time.sleep(1.5)
        city_total = get_pageviews(city["city_article"], BASELINE_START, BASELINE_END)
        time.sleep(1.5)
        baselines[city["name"]] = {
            "stadium_avg_weekly": round(stadium_total / BASELINE_WEEKS, 1),
            "city_avg_weekly":    round(city_total    / BASELINE_WEEKS, 1),
            "stadium_total":      stadium_total,
            "city_total":         city_total,
        }
        b = baselines[city["name"]]
        print("    stadium_avg=" + str(b["stadium_avg_weekly"]) +
              "/wk  city_avg=" + str(b["city_avg_weekly"]) + "/wk")
    return baselines


def load_existing_baselines(existing_data):
    """
    Reuse baselines stored from a previous run.
    Any city with a zero stadium or city baseline is flagged for re-fetch
    by returning None, which triggers fetch_baselines() to run again.
    Partial re-fetch: only re-fetches articles with zero baselines.
    """
    if not existing_data:
        return None
    cities = existing_data.get("cities", [])
    if not cities or "baselineStadiumAvgWeekly" not in cities[0]:
        return None
    result = {}
    needs_refetch = []
    for c in cities:
        result[c["name"]] = {
            "stadium_avg_weekly": c.get("baselineStadiumAvgWeekly", 0),
            "city_avg_weekly":    c.get("baselineCityAvgWeekly",    0),
            "stadium_total":      c.get("baselineStadiumTotal",     0),
            "city_total":         c.get("baselineCityTotal",        0),
        }
        if c.get("baselineStadiumAvgWeekly", 0) == 0:
            needs_refetch.append((c["name"], "stadium"))
        if c.get("baselineCityAvgWeekly", 0) == 0:
            needs_refetch.append((c["name"], "city"))

    if needs_refetch:
        print("  WARNING: Zero baselines found - will re-fetch:")
        for name, kind in needs_refetch:
            print("    -> " + name + " (" + kind + ")")
        return result, needs_refetch
    print("  All baselines valid - reusing from previous run.")
    return result, []


# ── Uplift calculation ─────────────────────────────────────────────────────────

def compute_uplift(views, avg_weekly_baseline):
    """views / avg_weekly * 100. Returns 0 if baseline missing."""
    if avg_weekly_baseline <= 0:
        return 0.0
    return round(views / avg_weekly_baseline * 100, 1)


def compute_combined_uplift(stadium_uplift, city_uplift):
    """2/3 stadium + 1/3 city weighted average."""
    return round(stadium_uplift * STADIUM_WEIGHT + city_uplift * CITY_WEIGHT, 1)


def uplift_to_points(combined_uplifts):
    """1st=10pts ... 10th=1pt, 11th-16th=0pts. No points if all zero."""
    if not combined_uplifts or max(combined_uplifts.values()) == 0:
        return {n: 0 for n in combined_uplifts}
    ranked = sorted(combined_uplifts.items(), key=lambda x: x[1], reverse=True)
    return {name: max(0, 10 - i) for i, (name, _) in enumerate(ranked)}


# ── Period fetch ───────────────────────────────────────────────────────────────

def fetch_period(label, start_date, end_date, baselines):
    """Fetch stadium + city views, compute weighted uplift and points."""
    days          = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    week_fraction = days / 7.0

    print("\n  [" + label + "] " + start_date + " to " + end_date)

    stadium_views   = {}
    city_views      = {}
    stadium_uplift  = {}
    city_uplift_map = {}
    combined_uplift = {}

    for city in CITIES:
        n  = city["name"]
        bl = baselines[n]

        sv = get_pageviews(city["stadium_article"], start_date, end_date)
        time.sleep(1.5)
        if sv == 0 and bl["stadium_avg_weekly"] > 0:
            print("    WARNING: " + n + " stadium returned 0 views (baseline=" +
                  str(bl["stadium_avg_weekly"]) + "/wk) - likely transient 429")
        cv = get_pageviews(city["city_article"], start_date, end_date)
        time.sleep(1.5)
        if cv == 0 and bl["city_avg_weekly"] > 0:
            print("    WARNING: " + n + " city returned 0 views (baseline=" +
                  str(bl["city_avg_weekly"]) + "/wk) - likely transient 429")

        # Normalise to 7-day equivalent
        sv_weekly = sv / week_fraction
        cv_weekly = cv / week_fraction

        su = compute_uplift(sv_weekly, bl["stadium_avg_weekly"])
        cu = compute_uplift(cv_weekly, bl["city_avg_weekly"])
        wu = compute_combined_uplift(su, cu)

        stadium_views[n]   = sv
        city_views[n]      = cv
        stadium_uplift[n]  = su
        city_uplift_map[n] = cu
        combined_uplift[n] = wu

        print("  " + n.ljust(25) +
              " stadium=" + str(su) + "x" +
              "  city=" + str(cu) + "x" +
              "  combined=" + str(wu) + "x")

    points = uplift_to_points(combined_uplift)

    top3 = sorted(combined_uplift.items(), key=lambda x: x[1], reverse=True)[:3]
    print("  Top 3: " + " | ".join(n + " (" + str(v) + "x)" for n, v in top3))

    return {
        "stadium_views":   stadium_views,
        "city_views":      city_views,
        "stadium_uplift":  stadium_uplift,
        "city_uplift":     city_uplift_map,
        "combined_uplift": combined_uplift,
        "points":          points,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Wikipedia Pageviews Uplift Tracker (2/3 stadium + 1/3 city)")
    today = date.today()

    # Load existing data to reuse baselines
    existing_data = None
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    loaded = load_existing_baselines(existing_data)
    if loaded is None:
        # No existing baselines at all - full fetch
        baselines = fetch_baselines()
    else:
        existing_baselines, needs_refetch = loaded
        if needs_refetch:
            # Partial re-fetch for zero baselines
            baselines = fetch_baselines(existing=existing_baselines, needs_refetch=needs_refetch)
        else:
            baselines = existing_baselines

    # Discrete tournament weeks
    week_data = {}
    for week in WEEKS:
        if today < date.fromisoformat(week["start"]):
            print("\nSkipping " + week["label"] + " (starts " + week["start"] + ")")
            continue
        print("\n=== " + week["label"] + " ===")
        week_data[week["label"]] = fetch_period(
            week["label"], week["start"], week["end"], baselines
        )

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

        week_points  = {}
        week_uplift  = {}
        week_stadium = {}
        week_city    = {}

        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                wd = week_data[lbl]
                week_points[lbl]  = wd["points"][n]
                week_uplift[lbl]  = wd["combined_uplift"][n]
                week_stadium[lbl] = wd["stadium_uplift"][n]
                week_city[lbl]    = wd["city_uplift"][n]
            else:
                week_points[lbl]  = None
                week_uplift[lbl]  = None
                week_stadium[lbl] = None
                week_city[lbl]    = None

        to_date = sum(v for v in week_points.values() if v is not None)

        results.append({
            "name":    n,
            "country": city["country"],
            "flag":    city["flag"],
            "region":  city["region"],
            "stadium": city["stadium"],
            "wikiUrl": city["wikiUrl"],
            # Baselines
            "baselineStadiumAvgWeekly": bl["stadium_avg_weekly"],
            "baselineCityAvgWeekly":    bl["city_avg_weekly"],
            "baselineStadiumTotal":     bl["stadium_total"],
            "baselineCityTotal":        bl["city_total"],
            # Last 7 days
            "lastWeekStadiumViews":   l7["stadium_views"][n],
            "lastWeekCityViews":      l7["city_views"][n],
            "lastWeekStadiumUplift":  l7["stadium_uplift"][n],
            "lastWeekCityUplift":     l7["city_uplift"][n],
            "lastWeekUplift":         l7["combined_uplift"][n],
            "lastWeekPts":            l7["points"][n],
            # Discrete weeks
            "weekPoints":       week_points,
            "weekUplift":       week_uplift,
            "weekStadiumUplift":week_stadium,
            "weekCityUplift":   week_city,
            "toDatePoints":     to_date,
        })

    results.sort(key=lambda x: (x["toDatePoints"], x["lastWeekUplift"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25) +
              "  stadium=" + str(city["lastWeekStadiumUplift"]) + "x" +
              "  city=" + str(city["lastWeekCityUplift"]) + "x" +
              "  combined=" + str(city["lastWeekUplift"]) + "x" +
              "  pts=" + str(city["lastWeekPts"]))

    now = datetime.now(timezone.utc)
    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "metric":         "Wikipedia uplift index: 2/3 stadium + 1/3 city vs 12-month baseline",
            "baselineWindow": BASELINE_START + " to " + BASELINE_END,
            "weights":        {"stadium": "2/3", "city": "1/3"},
            "weeks":          WEEKS,
            "cities":         results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")
    print("Top city: " + results[0]["name"] +
          " (combined uplift: " + str(results[0]["lastWeekUplift"]) + "x)")


main()
