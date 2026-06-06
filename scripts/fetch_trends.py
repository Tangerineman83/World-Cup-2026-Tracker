#!/usr/bin/env python3
"""
fetch_trends.py  —  Wikipedia Pageviews Uplift Edition

Metric: Stadium Wikipedia article pageviews, indexed against a 12-month baseline.

For each tournament week (and the rolling last-7-days window):
  uplift_index = (views_this_period / avg_weekly_views_last_12_months) * 100

  100 = exactly normal interest
  300 = 3x normal interest
  850 = 8.5x spike (strong World Cup effect)

This removes the "big city / famous stadium" bias. A smaller venue showing
a 10x spike ranks above a globally famous stadium showing only a 2x lift.
Points are awarded on the uplift index: 1st = 10pts ... 10th = 1pt, rest = 0.

Baseline is fetched once (June 2025 – May 2026) and stored in data.json
alongside weekly scores so the site can show "Normal: X views/week".
"""

import json
import time
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, date, timedelta

# ── Stadium articles only ──────────────────────────────────────────────────────
# City articles dropped - they reflect population size, not World Cup interest.
# Stadium articles are a clean signal: spikes are almost entirely event-driven.

CITIES = [
    {
        "name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",
        "stadium": "MetLife Stadium",
        "article": "MetLife_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/MetLife_Stadium",
    },
    {
        "name": "Los Angeles", "country": "USA", "flag": "US", "region": "West",
        "stadium": "SoFi Stadium",
        "article": "SoFi_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/SoFi_Stadium",
    },
    {
        "name": "Dallas", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "AT&T Stadium",
        "article": "AT%26T_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/AT%26T_Stadium",
    },
    {
        "name": "Mexico City", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium": "Estadio Azteca",
        "article": "Estadio_Azteca",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Azteca",
    },
    {
        "name": "Miami", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Hard Rock Stadium",
        "article": "Hard_Rock_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/Hard_Rock_Stadium",
    },
    {
        "name": "Atlanta", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "Mercedes-Benz Stadium",
        "article": "Mercedes-Benz_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium",
    },
    {
        "name": "San Francisco", "country": "USA", "flag": "US", "region": "West",
        "stadium": "Levi's Stadium",
        "article": "Levi%27s_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/Levi%27s_Stadium",
    },
    {
        "name": "Seattle", "country": "USA", "flag": "US", "region": "West",
        "stadium": "Lumen Field",
        "article": "Lumen_Field",
        "wikiUrl": "https://en.wikipedia.org/wiki/Lumen_Field",
    },
    {
        "name": "Toronto", "country": "CAN", "flag": "CA", "region": "East",
        "stadium": "BMO Field",
        "article": "BMO_Field",
        "wikiUrl": "https://en.wikipedia.org/wiki/BMO_Field",
    },
    {
        "name": "Boston", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Gillette Stadium",
        "article": "Gillette_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/Gillette_Stadium",
    },
    {
        "name": "Guadalajara", "country": "MEX", "flag": "MX", "region": "West",
        "stadium": "Estadio Akron",
        "article": "Estadio_Akron",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_Akron",
    },
    {
        "name": "Houston", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "NRG Stadium",
        "article": "NRG_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/NRG_Stadium",
    },
    {
        "name": "Philadelphia", "country": "USA", "flag": "US", "region": "East",
        "stadium": "Lincoln Financial Field",
        "article": "Lincoln_Financial_Field",
        "wikiUrl": "https://en.wikipedia.org/wiki/Lincoln_Financial_Field",
    },
    {
        "name": "Vancouver", "country": "CAN", "flag": "CA", "region": "West",
        "stadium": "BC Place",
        "article": "BC_Place",
        "wikiUrl": "https://en.wikipedia.org/wiki/BC_Place",
    },
    {
        "name": "Monterrey", "country": "MEX", "flag": "MX", "region": "Central",
        "stadium": "Estadio BBVA",
        "article": "Estadio_BBVA",
        "wikiUrl": "https://en.wikipedia.org/wiki/Estadio_BBVA",
    },
    {
        "name": "Kansas City", "country": "USA", "flag": "US", "region": "Central",
        "stadium": "Arrowhead Stadium",
        "article": "Arrowhead_Stadium",
        "wikiUrl": "https://en.wikipedia.org/wiki/Arrowhead_Stadium",
    },
]

WEEKS = [
    {"label": "Week 1", "start": "2026-06-11", "end": "2026-06-17"},
    {"label": "Week 2", "start": "2026-06-18", "end": "2026-06-24"},
    {"label": "Week 3", "start": "2026-06-25", "end": "2026-07-01"},
    {"label": "Week 4", "start": "2026-07-02", "end": "2026-07-08"},
]

# 12-month baseline window: June 2025 – May 2026 (pre-tournament)
BASELINE_START = "2025-06-01"
BASELINE_END   = "2026-05-31"
BASELINE_WEEKS = 52

WIKI_AGENT = "WC2026UpliftTracker/1.0 (public research; github.com/tracker)"


# ── API helpers ────────────────────────────────────────────────────────────────

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

def fetch_baselines():
    """
    Fetch 12-month pageview totals for all stadiums (Jun 2025 - May 2026).
    Returns dict of {name: avg_weekly_views}.
    This is fetched once and stored in data.json so future runs can reuse it,
    avoiding 52 weeks of API calls every Saturday.
    """
    print("\n=== Fetching 12-month baselines (Jun 2025 - May 2026) ===")
    baselines = {}
    for city in CITIES:
        total = get_pageviews(city["article"], BASELINE_START, BASELINE_END)
        avg_weekly = round(total / BASELINE_WEEKS, 1)
        baselines[city["name"]] = {
            "total":      total,
            "avg_weekly": avg_weekly,
        }
        print("  " + city["name"].ljust(25) +
              " total=" + str(total) + "  avg_weekly=" + str(avg_weekly))
        time.sleep(1.5)
    return baselines


def load_existing_baselines(existing_data):
    """Reuse baselines from a previous run if they exist - avoids refetching."""
    if not existing_data:
        return None
    cities = existing_data.get("cities", [])
    if not cities or "baselineAvgWeekly" not in cities[0]:
        return None
    result = {}
    for city in cities:
        result[city["name"]] = {
            "total":      city.get("baselineTotal", 0),
            "avg_weekly": city.get("baselineAvgWeekly", 0),
        }
    print("  Reusing baselines from previous run.")
    return result


# ── Uplift scoring ─────────────────────────────────────────────────────────────

def compute_uplift(views_this_week, avg_weekly_baseline):
    """
    Uplift index = (actual views / baseline avg) * 100
    100 = normal, 200 = 2x normal, 500 = 5x spike etc.
    Returns 0 if baseline is zero (avoids division error).
    """
    if avg_weekly_baseline <= 0:
        return 0
    return round(views_this_week / avg_weekly_baseline * 100, 1)


def uplift_to_points(uplift_scores):
    """1st=10pts ... 10th=1pt, 11th-16th=0pts. No points if all zero."""
    if not uplift_scores or max(uplift_scores.values()) == 0:
        return {name: 0 for name in uplift_scores}
    ranked = sorted(uplift_scores.items(), key=lambda x: x[1], reverse=True)
    return {name: max(0, 10 - i) for i, (name, _) in enumerate(ranked)}


# ── Period fetch ───────────────────────────────────────────────────────────────

def fetch_period(label, start_date, end_date, baselines):
    """Fetch views for all stadiums, compute uplift index and points."""
    days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    week_fraction = days / 7.0  # normalise to weekly equivalent

    print("\n  [" + label + "] " + start_date + " to " + end_date +
          " (" + str(days) + " days)")

    raw_views  = {}
    uplift_idx = {}

    for city in CITIES:
        views = get_pageviews(city["article"], start_date, end_date)
        # Normalise to 7-day equivalent so short periods are comparable
        weekly_equiv = views / week_fraction
        uplift = compute_uplift(weekly_equiv, baselines[city["name"]]["avg_weekly"])
        raw_views[city["name"]]  = views
        uplift_idx[city["name"]] = uplift
        print("  " + city["name"].ljust(25) +
              " views=" + str(views) +
              "  weekly_equiv=" + str(round(weekly_equiv)) +
              "  uplift=" + str(uplift) + "x")
        time.sleep(1.5)

    points = uplift_to_points(uplift_idx)

    top3 = sorted(uplift_idx.items(), key=lambda x: x[1], reverse=True)[:3]
    print("  Top 3: " + " | ".join(n + " (" + str(v) + "x)" for n, v in top3))
    return raw_views, uplift_idx, points


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Wikipedia Pageviews Uplift Tracker")
    print("Metric: stadium views vs 12-month baseline (uplift index)")

    today = date.today()

    # Load existing data to reuse baselines if available
    existing_data = None
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing_data = json.load(f)
            print("Loaded existing data.json")
        except Exception:
            pass

    # Baselines: reuse if available, otherwise fetch
    baselines = load_existing_baselines(existing_data)
    if not baselines:
        baselines = fetch_baselines()
    else:
        print("  Baselines reused from previous run - skipping 12-month fetch")

    # Discrete tournament weeks
    week_data = {}
    for week in WEEKS:
        if today < date.fromisoformat(week["start"]):
            print("\nSkipping " + week["label"] + " (starts " + week["start"] + ")")
            continue
        print("\n=== " + week["label"] + " ===")
        raw, uplift, pts = fetch_period(
            week["label"], week["start"], week["end"], baselines
        )
        week_data[week["label"]] = {"raw": raw, "uplift": uplift, "points": pts}

    # Rolling last 7 days
    print("\n=== Last 7 Days (rolling) ===")
    l7_end   = today.strftime("%Y-%m-%d")
    l7_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    l7_raw, l7_uplift, l7_pts = fetch_period(
        "Last 7 days", l7_start, l7_end, baselines
    )

    # Build results
    results = []
    for city in CITIES:
        n = city["name"]
        week_points = {}
        week_uplift = {}
        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                week_points[lbl] = week_data[lbl]["points"][n]
                week_uplift[lbl] = week_data[lbl]["uplift"][n]
            else:
                week_points[lbl] = None
                week_uplift[lbl] = None

        to_date = sum(v for v in week_points.values() if v is not None)

        results.append({
            "name":              n,
            "country":           city["country"],
            "flag":              city["flag"],
            "region":            city["region"],
            "stadium":           city["stadium"],
            "wikiUrl":           city["wikiUrl"],
            # Baseline
            "baselineTotal":     baselines[n]["total"],
            "baselineAvgWeekly": baselines[n]["avg_weekly"],
            # Last 7 days
            "lastWeekViews":     l7_raw.get(n, 0),
            "lastWeekUplift":    l7_uplift.get(n, 0),
            "lastWeekPts":       l7_pts.get(n, 0),
            # Discrete weeks
            "weekPoints":        week_points,
            "weekUplift":        week_uplift,
            "toDatePoints":      to_date,
        })

    results.sort(key=lambda x: (x["toDatePoints"], x["lastWeekUplift"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25) +
              "  baseline=" + str(city["baselineAvgWeekly"]) + "/wk" +
              "  uplift=" + str(city["lastWeekUplift"]) + "x" +
              "  pts=" + str(city["lastWeekPts"]) +
              "  toDate=" + str(city["toDatePoints"]))

    now = datetime.now(timezone.utc)
    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "metric":         "Wikipedia stadium pageviews vs 12-month baseline (uplift index)",
            "baselineWindow": BASELINE_START + " to " + BASELINE_END,
            "weeks":          WEEKS,
            "cities":         results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")
    print("Top city: " + results[0]["name"] +
          " (uplift: " + str(results[0]["lastWeekUplift"]) + "x)")


main()
