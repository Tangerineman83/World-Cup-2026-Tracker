#!/usr/bin/env python3
"""
fetch_trends.py  —  Wikipedia Pageviews Edition

Fetches daily Wikipedia pageview counts for each host city's:
  - City article       (destination/economic interest signal)
  - Stadium article    (event-specific interest signal)

Combined score = city_views + stadium_views for the period.
Scores are normalised so the top city = 100, then points awarded 10→0.

Wikimedia pageviews API is fully open, no authentication required,
and works reliably from GitHub Actions.

API docs: https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews
"""

import json
import time
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, date, timedelta

# ── City + Stadium Wikipedia article pairs ─────────────────────────────────────
# Article titles must match the exact Wikipedia URL slug (spaces as underscores).
# Stadium = the real/permanent name (not the temporary FIFA tournament name).

CITIES = [
    {
        "name":    "New York / New Jersey",
        "country": "USA", "flag": "US", "region": "East",
        "city_article":    "New_York_City",
        "stadium_article": "MetLife_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/MetLife_Stadium",
    },
    {
        "name":    "Los Angeles",
        "country": "USA", "flag": "US", "region": "West",
        "city_article":    "Los_Angeles",
        "stadium_article": "SoFi_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/SoFi_Stadium",
    },
    {
        "name":    "Dallas",
        "country": "USA", "flag": "US", "region": "Central",
        "city_article":    "Dallas",
        "stadium_article": "AT%26T_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/AT%26T_Stadium",
    },
    {
        "name":    "Mexico City",
        "country": "MEX", "flag": "MX", "region": "Central",
        "city_article":    "Mexico_City",
        "stadium_article": "Estadio_Azteca",
        "trendsUrl": "https://en.wikipedia.org/wiki/Estadio_Azteca",
    },
    {
        "name":    "Miami",
        "country": "USA", "flag": "US", "region": "East",
        "city_article":    "Miami",
        "stadium_article": "Hard_Rock_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/Hard_Rock_Stadium",
    },
    {
        "name":    "Atlanta",
        "country": "USA", "flag": "US", "region": "Central",
        "city_article":    "Atlanta",
        "stadium_article": "Mercedes-Benz_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/Mercedes-Benz_Stadium",
    },
    {
        "name":    "San Francisco",
        "country": "USA", "flag": "US", "region": "West",
        "city_article":    "San_Francisco",
        "stadium_article": "Levi%27s_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/Levi%27s_Stadium",
    },
    {
        "name":    "Seattle",
        "country": "USA", "flag": "US", "region": "West",
        "city_article":    "Seattle",
        "stadium_article": "Lumen_Field",
        "trendsUrl": "https://en.wikipedia.org/wiki/Lumen_Field",
    },
    {
        "name":    "Toronto",
        "country": "CAN", "flag": "CA", "region": "East",
        "city_article":    "Toronto",
        "stadium_article": "BMO_Field",
        "trendsUrl": "https://en.wikipedia.org/wiki/BMO_Field",
    },
    {
        "name":    "Boston",
        "country": "USA", "flag": "US", "region": "East",
        "city_article":    "Boston",
        "stadium_article": "Gillette_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/Gillette_Stadium",
    },
    {
        "name":    "Guadalajara",
        "country": "MEX", "flag": "MX", "region": "West",
        "city_article":    "Guadalajara",
        "stadium_article": "Estadio_Akron",
        "trendsUrl": "https://en.wikipedia.org/wiki/Estadio_Akron",
    },
    {
        "name":    "Houston",
        "country": "USA", "flag": "US", "region": "Central",
        "city_article":    "Houston",
        "stadium_article": "NRG_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/NRG_Stadium",
    },
    {
        "name":    "Philadelphia",
        "country": "USA", "flag": "US", "region": "East",
        "city_article":    "Philadelphia",
        "stadium_article": "Lincoln_Financial_Field",
        "trendsUrl": "https://en.wikipedia.org/wiki/Lincoln_Financial_Field",
    },
    {
        "name":    "Vancouver",
        "country": "CAN", "flag": "CA", "region": "West",
        "city_article":    "Vancouver",
        "stadium_article": "BC_Place",
        "trendsUrl": "https://en.wikipedia.org/wiki/BC_Place",
    },
    {
        "name":    "Monterrey",
        "country": "MEX", "flag": "MX", "region": "Central",
        "city_article":    "Monterrey",
        "stadium_article": "Estadio_BBVA",
        "trendsUrl": "https://en.wikipedia.org/wiki/Estadio_BBVA",
    },
    {
        "name":    "Kansas City",
        "country": "USA", "flag": "US", "region": "Central",
        "city_article":    "Kansas_City,_Missouri",
        "stadium_article": "Arrowhead_Stadium",
        "trendsUrl": "https://en.wikipedia.org/wiki/Arrowhead_Stadium",
    },
]

WEEKS = [
    {"label": "Week 1", "start": "2026-06-11", "end": "2026-06-17"},
    {"label": "Week 2", "start": "2026-06-18", "end": "2026-06-24"},
    {"label": "Week 3", "start": "2026-06-25", "end": "2026-07-01"},
    {"label": "Week 4", "start": "2026-07-02", "end": "2026-07-08"},
]

WIKI_AGENT = "WC2026Tracker/1.0 (https://github.com; public research project)"


# ── Wikipedia API helpers ──────────────────────────────────────────────────────

def get_pageviews(article, start_date, end_date, retries=4):
    """
    Fetch total Wikipedia pageviews for an article between start_date and end_date.
    Dates as 'YYYY-MM-DD' strings. Returns integer total, or 0 on failure.
    Retries on 429 (rate limit) with exponential backoff.
    """
    start = start_date.replace("-", "")
    end   = end_date.replace("-", "")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/all-agents/" + article + "/daily/" + start + "/" + end
    )
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": WIKI_AGENT})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                return sum(item["views"] for item in data.get("items", []))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (2 ** attempt)  # 5, 10, 20, 40 seconds
                print("    429 rate limit - waiting " + str(wait) + "s before retry...")
                time.sleep(wait)
                continue
            elif e.code == 404:
                print("    404 - article not found: " + article)
                return 0
            else:
                print("    HTTP error " + str(e.code) + " for " + article)
                return 0
        except Exception as e:
            print("    Error fetching " + article + ": " + str(e))
            return 0
    print("    All retries failed for: " + article)
    return 0


def get_combined_views(city, start_date, end_date):
    """Fetch city + stadium pageviews and return combined total."""
    city_views    = get_pageviews(city["city_article"],    start_date, end_date)
    stadium_views = get_pageviews(city["stadium_article"], start_date, end_date)
    total = city_views + stadium_views
    print(f"    {city['name']:<25} city={city_views:>7,}  stadium={stadium_views:>7,}  total={total:>8,}")
    time.sleep(1.5)  # be polite to Wikimedia - prevents 429 rate limiting
    return total


# ── Scoring helpers ────────────────────────────────────────────────────────────

def normalise(raw_scores):
    """Express all scores as 0-100 relative to the highest-scoring city."""
    best = max(raw_scores.values()) if raw_scores else 0
    if best == 0:
        return {k: 0 for k in raw_scores}
    return {k: min(100, int(round(v / best * 100))) for k, v in raw_scores.items()}


def scores_to_points(normalised_scores):
    """1st=10pts, 2nd=9pts ... 10th=1pt, 11th-16th=0pts.
    If all scores are zero (fetch failed), everyone gets 0 - no points awarded."""
    if not normalised_scores or max(normalised_scores.values()) == 0:
        return {name: 0 for name in normalised_scores}
    ranked = sorted(normalised_scores.items(), key=lambda x: x[1], reverse=True)
    points = {}
    for i, (name, _) in enumerate(ranked):
        points[name] = max(0, 10 - i)
    return points


# ── Date helpers ───────────────────────────────────────────────────────────────

def last_7_days():
    today = date.today()
    start = today - timedelta(days=7)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def week_available(week):
    return date.today() >= date.fromisoformat(week["start"])


# ── Main fetch ─────────────────────────────────────────────────────────────────

def fetch_period(label, start_date, end_date):
    """Fetch combined city+stadium views for all 16 cities over a date range."""
    print(f"\n  [{label}] {start_date} to {end_date}")
    raw = {}
    for city in CITIES:
        raw[city["name"]] = get_combined_views(city, start_date, end_date)
    norm   = normalise(raw)
    points = scores_to_points(norm)
    print(f"  Top 3: " + ", ".join(
        f"{n}={norm[n]}" for n, _ in sorted(norm.items(), key=lambda x: x[1], reverse=True)[:3]
    ))
    return raw, norm, points


def fetch_all():
    # Discrete tournament weeks
    week_data = {}
    for week in WEEKS:
        if not week_available(week):
            print(f"\nSkipping {week['label']} (starts {week['start']})")
            continue
        print(f"\n=== {week['label']} ===")
        raw, norm, pts = fetch_period(week["label"], week["start"], week["end"])
        week_data[week["label"]] = {"raw": raw, "norm": norm, "points": pts}

    # Rolling last 7 days
    print("\n=== Last 7 Days (rolling) ===")
    l7_start, l7_end = last_7_days()
    l7_raw, l7_norm, l7_pts = fetch_period("Last 7 days", l7_start, l7_end)

    # Build results
    results = []
    for city in CITIES:
        n = city["name"]
        week_points = {}
        week_scores = {}
        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                week_points[lbl] = week_data[lbl]["points"][n]
                week_scores[lbl] = week_data[lbl]["norm"][n]
            else:
                week_points[lbl] = None
                week_scores[lbl] = None

        to_date = sum(v for v in week_points.values() if v is not None)

        results.append({
            "name":          n,
            "country":       city["country"],
            "flag":          city["flag"],
            "region":        city["region"],
            "trendsUrl":     city["trendsUrl"],
            "lastWeekScore": l7_norm.get(n, 0),
            "lastWeekPts":   l7_pts.get(n, 0),
            "lastWeekRaw":   l7_raw.get(n, 0),
            "weekPoints":    week_points,
            "weekScores":    week_scores,
            "toDatePoints":  to_date,
        })

    results.sort(key=lambda x: (x["toDatePoints"], x["lastWeekPts"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print(f"  {city['name']:<25}  idx={city['lastWeekScore']:>3}  pts={city['lastWeekPts']:>2}  toDate={city['toDatePoints']:>3}")

    return results


def main():
    print("Fetching Wikipedia pageviews for 16 World Cup host cities...")
    print("Metric: city article + stadium article daily pageviews (combined)")
    data = fetch_all()
    now  = datetime.now(timezone.utc)

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "metric":         "Wikipedia pageviews (city + stadium articles combined)",
            "weeks":          WEEKS,
            "cities":         data,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")
    print("Top city: " + data[0]["name"])


main()
