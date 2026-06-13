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

# Weights (city Wikipedia removed — added noise, not signal)
STADIUM_WEIGHT    = 0.50
WIKIVOYAGE_WEIGHT = 0.50

# Wikivoyage noise controls (as index values: 100 = 1x, 1000 = 10x)
WIKIVOYAGE_FLOOR    = 100.0   # 1.0x minimum
WIKIVOYAGE_CAP      = 1000.0  # 10.0x maximum
WIKIVOYAGE_LOW_CONF = 150     # avg views/week below this = flag as low confidence

WIKI_AGENT = "WC2026UpliftTracker/1.0 (public research; github.com/tracker)"


# ── API ───────────────────────────────────────────────────────────────────────

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
    """Shorthand for English Wikipedia."""
    return get_pageviews("en.wikipedia", article, start, end)


def voyage(article, start, end):
    """Shorthand for English Wikivoyage."""
    return get_pageviews("en.wikivoyage", article, start, end)


# ── Uplift calculation ──────────────────────────────────────────────────────────

def uplift(views, avg_weekly, week_fraction=1.0):
    """Raw uplift index (100 = 1.0x). Returns 0.0 if baseline missing."""
    if avg_weekly <= 0:
        return 0.0
    return round((views / week_fraction) / avg_weekly * 100, 1)


def clamp_wikivoyage(raw, low_conf=False):
    """
    Apply floor and cap to Wikivoyage uplift.
    Floor: 100 (1.0x) — prevents noisy below-baseline weeks dragging score down.
    Cap:  1000 (10.0x) — prevents outlier spikes on small samples inflating score.
    Low-confidence baseline (<150 views/week): cap reduced to 500 (5x).
    """
    cap = 500.0 if low_conf else WIKIVOYAGE_CAP
    return round(max(WIKIVOYAGE_FLOOR, min(cap, raw)), 1)


def combined(stadium_u, wikivoyage_u):
    """Weighted combination of the two uplift signals (50/50)."""
    return round(stadium_u * STADIUM_WEIGHT + wikivoyage_u * WIKIVOYAGE_WEIGHT, 1)


def to_points(scores):
    """1st=10pts ... 10th=1pt, 11th-16th=0pts. No points if all zero."""
    if not scores or max(scores.values()) == 0:
        return {n: 0 for n in scores}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {name: max(0, 10 - i) for i, (name, _) in enumerate(ranked)}


# ── GDP Impact estimates (static — modelled, not fetched) ────────────────────────
# Scope: direct incremental tourist/visitor spend only.
# Excludes: FIFA operational spend, host city infrastructure, supply chain effects.
# Methodology: stadium capacity × 95% occupancy × visitor shares × city-adjusted
#              spend × (1 - displacement tier) × city-specific multiplier
# Full methodology at assumptions.html
GDP_IMPACT = {
    "Monterrey": {"impact_usd_m": 224, "pct_annual_gdp": 0.264, "metro_gdp_usd_bn": 85, "tier": "Low-tourism City", "displacement_pct": 8, "multiplier": 1.25, "capacity": 53500, "intl_per_match": 12706, "domestic_per_match": 17789, "col_factor": 0.533, "intl_daily": 306.0, "beer_usd": 5.49, "hotel_rate_usd": 538, "hotel_premium_pct": 104},
    "Kansas City": {"impact_usd_m": 414, "pct_annual_gdp": 0.23, "metro_gdp_usd_bn": 180, "tier": "Low-tourism City", "displacement_pct": 8, "multiplier": 1.55, "capacity": 76416, "intl_per_match": 18149, "domestic_per_match": 25408, "col_factor": 0.814, "intl_daily": 385.0, "beer_usd": 8.72, "hotel_rate_usd": 344, "hotel_premium_pct": 30},
    "Guadalajara": {"impact_usd_m": 151, "pct_annual_gdp": 0.222, "metro_gdp_usd_bn": 68, "tier": "Low-tourism City", "displacement_pct": 8, "multiplier": 1.3, "capacity": 48000, "intl_per_match": 11400, "domestic_per_match": 15960, "col_factor": 0.459, "intl_daily": 285.0, "beer_usd": 2.58, "hotel_rate_usd": 511, "hotel_premium_pct": 58},
    "Vancouver": {"impact_usd_m": 239, "pct_annual_gdp": 0.184, "metro_gdp_usd_bn": 130, "tier": "Global Gateway", "displacement_pct": 35, "multiplier": 1.1, "capacity": 54500, "intl_per_match": 12944, "domestic_per_match": 18121, "col_factor": 0.726, "intl_daily": 360.0, "beer_usd": 8.05, "hotel_rate_usd": 775, "hotel_premium_pct": 55},
    "Atlanta": {"impact_usd_m": 469, "pct_annual_gdp": 0.104, "metro_gdp_usd_bn": 450, "tier": "Mid-tier Host", "displacement_pct": 15, "multiplier": 1.65, "capacity": 75000, "intl_per_match": 17812, "domestic_per_match": 24938, "col_factor": 0.835, "intl_daily": 390.0, "beer_usd": 8.05, "hotel_rate_usd": 220, "hotel_premium_pct": 2},
    "Boston": {"impact_usd_m": 492, "pct_annual_gdp": 0.093, "metro_gdp_usd_bn": 530, "tier": "Major Regional Hub", "displacement_pct": 25, "multiplier": 1.8, "capacity": 65878, "intl_per_match": 15646, "domestic_per_match": 21904, "col_factor": 0.881, "intl_daily": 403.0, "beer_usd": 8.12, "hotel_rate_usd": 611, "hotel_premium_pct": 42},
    "Seattle": {"impact_usd_m": 366, "pct_annual_gdp": 0.083, "metro_gdp_usd_bn": 440, "tier": "Major Regional Hub", "displacement_pct": 25, "multiplier": 1.75, "capacity": 69000, "intl_per_match": 16388, "domestic_per_match": 22942, "col_factor": 0.899, "intl_daily": 408.0, "beer_usd": 9.2, "hotel_rate_usd": 446, "hotel_premium_pct": 25},
    "Miami": {"impact_usd_m": 354, "pct_annual_gdp": 0.082, "metro_gdp_usd_bn": 430, "tier": "Global Gateway", "displacement_pct": 35, "multiplier": 1.75, "capacity": 65326, "intl_per_match": 15515, "domestic_per_match": 21721, "col_factor": 0.993, "intl_daily": 435.0, "beer_usd": 11.35, "hotel_rate_usd": 378, "hotel_premium_pct": 20},
    "Dallas": {"impact_usd_m": 634, "pct_annual_gdp": 0.078, "metro_gdp_usd_bn": 815, "tier": "Mid-tier Host", "displacement_pct": 15, "multiplier": 1.65, "capacity": 94000, "intl_per_match": 22325, "domestic_per_match": 31255, "col_factor": 0.769, "intl_daily": 372.0, "beer_usd": 9.2, "hotel_rate_usd": 272, "hotel_premium_pct": 3},
    "Philadelphia": {"impact_usd_m": 311, "pct_annual_gdp": 0.063, "metro_gdp_usd_bn": 490, "tier": "Mid-tier Host", "displacement_pct": 15, "multiplier": 1.65, "capacity": 69328, "intl_per_match": 16465, "domestic_per_match": 23052, "col_factor": 0.734, "intl_daily": 362.0, "beer_usd": 10.65, "hotel_rate_usd": 376, "hotel_premium_pct": 6},
    "Mexico City": {"impact_usd_m": 245, "pct_annual_gdp": 0.058, "metro_gdp_usd_bn": 420, "tier": "Global Gateway", "displacement_pct": 35, "multiplier": 1.4, "capacity": 87500, "intl_per_match": 20781, "domestic_per_match": 29094, "col_factor": 0.504, "intl_daily": 298.0, "beer_usd": 2.58, "hotel_rate_usd": 597, "hotel_premium_pct": 38},
    "Houston": {"impact_usd_m": 323, "pct_annual_gdp": 0.058, "metro_gdp_usd_bn": 560, "tier": "Major Regional Hub", "displacement_pct": 25, "multiplier": 1.65, "capacity": 72220, "intl_per_match": 17152, "domestic_per_match": 24013, "col_factor": 0.706, "intl_daily": 354.0, "beer_usd": 12.1, "hotel_rate_usd": 205, "hotel_premium_pct": 8},
    "San Francisco": {"impact_usd_m": 369, "pct_annual_gdp": 0.051, "metro_gdp_usd_bn": 720, "tier": "Major Regional Hub", "displacement_pct": 25, "multiplier": 1.8, "capacity": 71000, "intl_per_match": 16862, "domestic_per_match": 23608, "col_factor": 0.998, "intl_daily": 436.0, "beer_usd": 13.25, "hotel_rate_usd": 279, "hotel_premium_pct": 10},
    "Toronto": {"impact_usd_m": 145, "pct_annual_gdp": 0.045, "metro_gdp_usd_bn": 320, "tier": "Major Regional Hub", "displacement_pct": 25, "multiplier": 1.15, "capacity": 45000, "intl_per_match": 10688, "domestic_per_match": 14962, "col_factor": 0.693, "intl_daily": 351.0, "beer_usd": 8.4, "hotel_rate_usd": 593, "hotel_premium_pct": 25},
    "Los Angeles": {"impact_usd_m": 398, "pct_annual_gdp": 0.035, "metro_gdp_usd_bn": 1150, "tier": "Global Gateway", "displacement_pct": 35, "multiplier": 1.8, "capacity": 70240, "intl_per_match": 16682, "domestic_per_match": 23355, "col_factor": 0.885, "intl_daily": 405.0, "beer_usd": 13.25, "hotel_rate_usd": 383, "hotel_premium_pct": 10},
    "New York / New Jersey": {"impact_usd_m": 557, "pct_annual_gdp": 0.027, "metro_gdp_usd_bn": 2100, "tier": "Global Gateway", "displacement_pct": 35, "multiplier": 1.85, "capacity": 82500, "intl_per_match": 19594, "domestic_per_match": 27431, "col_factor": 1.0, "intl_daily": 437.0, "beer_usd": 12.3, "hotel_rate_usd": 645, "hotel_premium_pct": 15},
}

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

# Full 2026 World Cup schedule — static lookup, no API calls required.
# All 104 matches with UTC kickoff datetimes, confirmed through to the Final
# (19 July 2026). Source: FIFA official schedule via kickoffclock.com.
#
# A match counts as "played" once its kickoff time plus a buffer for match
# duration (2.5 hours, covering 90 minutes + stoppage/halftime/extra time
# margin) is in the past relative to the script's run time (UTC). This lets
# the script run more than once per day and pick up same-day results as soon
# as they're realistically available, while group-stage groups of 3
# simultaneous matches per city are each tracked individually.
CITY_MATCH_KICKOFFS = {
    "Mexico City": ["2026-06-11T19:00:00", "2026-06-18T02:00:00", "2026-06-25T01:00:00", "2026-07-01T01:00:00", "2026-07-06T00:00:00"],
    "Guadalajara": ["2026-06-12T02:00:00", "2026-06-19T01:00:00", "2026-06-24T02:00:00", "2026-06-27T00:00:00"],
    "Toronto": ["2026-06-12T19:00:00", "2026-06-17T23:00:00", "2026-06-20T20:00:00", "2026-06-23T23:00:00", "2026-06-26T19:00:00", "2026-07-02T23:00:00"],
    "Los Angeles": ["2026-06-13T01:00:00", "2026-06-16T01:00:00", "2026-06-18T19:00:00", "2026-06-21T19:00:00", "2026-06-26T02:00:00", "2026-06-28T19:00:00", "2026-07-02T19:00:00", "2026-07-10T19:00:00"],
    "San Francisco": ["2026-06-13T19:00:00", "2026-06-17T04:00:00", "2026-06-20T03:00:00", "2026-06-23T03:00:00", "2026-06-26T02:00:00", "2026-07-02T00:00:00"],
    "New York / New Jersey": ["2026-06-13T22:00:00", "2026-06-16T19:00:00", "2026-06-23T00:00:00", "2026-06-25T20:00:00", "2026-06-27T21:00:00", "2026-06-30T21:00:00", "2026-07-05T20:00:00", "2026-07-19T19:00:00"],
    "Boston": ["2026-06-14T01:00:00", "2026-06-16T22:00:00", "2026-06-19T22:00:00", "2026-06-23T20:00:00", "2026-06-26T19:00:00", "2026-06-29T20:30:00", "2026-07-09T20:00:00"],
    "Vancouver": ["2026-06-14T16:00:00", "2026-06-18T22:00:00", "2026-06-22T01:00:00", "2026-06-24T19:00:00", "2026-06-27T03:00:00", "2026-07-03T03:00:00", "2026-07-07T20:00:00"],
    "Houston": ["2026-06-14T17:00:00", "2026-06-17T17:00:00", "2026-06-20T17:00:00", "2026-06-23T17:00:00", "2026-06-27T00:00:00", "2026-06-29T17:00:00", "2026-07-04T17:00:00"],
    "Dallas": ["2026-06-14T20:00:00", "2026-06-17T20:00:00", "2026-06-22T17:00:00", "2026-06-25T23:00:00", "2026-06-28T02:00:00", "2026-06-30T17:00:00", "2026-07-03T18:00:00", "2026-07-06T19:00:00", "2026-07-14T19:00:00"],
    "Philadelphia": ["2026-06-14T23:00:00", "2026-06-20T00:30:00", "2026-06-22T21:00:00", "2026-06-25T20:00:00", "2026-06-27T21:00:00", "2026-07-04T21:00:00"],
    "Monterrey": ["2026-06-15T02:00:00", "2026-06-21T04:00:00", "2026-06-25T01:00:00", "2026-06-30T01:00:00"],
    "Atlanta": ["2026-06-15T16:00:00", "2026-06-18T16:00:00", "2026-06-21T16:00:00", "2026-06-24T22:00:00", "2026-06-27T23:30:00", "2026-07-01T16:00:00", "2026-07-07T16:00:00", "2026-07-15T19:00:00"],
    "Seattle": ["2026-06-15T19:00:00", "2026-06-19T19:00:00", "2026-06-24T19:00:00", "2026-06-27T03:00:00", "2026-07-01T20:00:00", "2026-07-07T00:00:00"],
    "Miami": ["2026-06-15T22:00:00", "2026-06-21T22:00:00", "2026-06-24T22:00:00", "2026-06-27T23:30:00", "2026-07-03T22:00:00", "2026-07-11T21:00:00", "2026-07-18T21:00:00"],
    "Kansas City": ["2026-06-17T01:00:00", "2026-06-21T00:00:00", "2026-06-25T23:00:00", "2026-06-28T02:00:00", "2026-07-04T01:30:00", "2026-07-12T01:00:00"],
}

MATCH_DURATION_BUFFER = timedelta(hours=2, minutes=30)


def get_match_counts():
    """
    Static schedule lookup: for each city, count matches scheduled and matches
    played. A match is "played" once kickoff time + 2.5hrs has passed (UTC).
    No network call required - works correctly however many times per day
    the script runs.
    """
    now = datetime.now(timezone.utc)
    counts = {}
    for city, kickoffs in CITY_MATCH_KICKOFFS.items():
        total  = len(kickoffs)
        played = 0
        for ko_str in kickoffs:
            kickoff = datetime.fromisoformat(ko_str).replace(tzinfo=timezone.utc)
            if kickoff + MATCH_DURATION_BUFFER < now:
                played += 1
        counts[city] = {"total": total, "played": played}

    total_scheduled = sum(c["total"]  for c in counts.values())
    total_played    = sum(c["played"] for c in counts.values())
    print("  Schedule (static): " + str(total_scheduled) + " scheduled, "
          + str(total_played) + " played (as of " + now.strftime("%Y-%m-%d %H:%M UTC") + ")")
    return counts


# ── Git helper ──────────────────────────────────────────────────────────────

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


# ── Baseline ────────────────────────────────────────────────────────────────

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
        s_total = v_total = 0

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
        print("    stadium=" + str(s_avg) + "/wk  voyage=" + str(v_avg) + "/wk"
              + (" [LOW CONF]" if v_low else ""))

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


# ── Current week fetch ────────────────────────────────────────────────────────

def fetch_current_week(l7_start, l7_end, baselines):
    """Fetch actual last-7-days views and compute uplift + points."""
    days = (date.fromisoformat(l7_end) - date.fromisoformat(l7_start)).days + 1
    wf   = days / 7.0

    print("\n=== Fetching last 7 days (" + l7_start + " to " + l7_end + ") ===")
    print("    Signals: stadium Wikipedia (50%) + Wikivoyage (50%)")

    stadium_u = {}; voyage_u = {}; combined_u = {}

    for city in CITIES:
        n  = city["name"]
        bl = baselines.get(n, {})

        sv = wiki(city["stadium_article"],     l7_start, l7_end); time.sleep(1.5)
        vv = voyage(city["wikivoyage_article"], l7_start, l7_end); time.sleep(1.5)

        if sv == 0 and bl.get("stadium_avg_weekly", 0) > 0:
            print("    Zero views for " + n + " stadium (baseline=" + str(bl.get("stadium_avg_weekly")) + ") - retrying in 20s...")
            time.sleep(20)
            sv = wiki(city["stadium_article"], l7_start, l7_end)
            if sv > 0:
                print("    Retry succeeded: " + str(sv) + " views")

        if vv == 0 and bl.get("wikivoyage_avg_weekly", 0) > 0:
            print("    Zero views for " + n + " wikivoyage (baseline=" + str(bl.get("wikivoyage_avg_weekly")) + ") - retrying in 20s...")
            time.sleep(20)
            vv = voyage(city["wikivoyage_article"], l7_start, l7_end)
            if vv > 0:
                print("    Retry succeeded: " + str(vv) + " views")

        su     = uplift(sv, bl.get("stadium_avg_weekly",    0), wf)
        vu_raw = uplift(vv, bl.get("wikivoyage_avg_weekly", 0), wf)
        vu     = clamp_wikivoyage(vu_raw, bl.get("wikivoyage_low_conf", False))

        # Floor stadium uplift at 1.0x - prevents transient API failures from
        # collapsing a city's ranking to zero.
        su = max(su, 100.0) if su > 0 else 100.0

        wu = combined(su, vu)

        stadium_u[n] = su; voyage_u[n] = vu; combined_u[n] = wu

        print("  " + n.ljust(25) + " stadium=" + str(su/100) + "x"
              + "  voyage=" + str(vu/100) + "x"
              + "  combined=" + str(wu/100) + "x")

    pts = to_points(combined_u)
    return {"stadium": stadium_u, "voyage": voyage_u,
            "combined": combined_u, "points": pts}


# ── Main ────────────────────────────────────────────────────────────────────

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

    # Match schedule (static lookup, no API call)
    print("\nLooking up match schedule...")
    match_counts = get_match_counts()

    # Fetch current week
    current = fetch_current_week(l7_start, l7_end, baselines)

    # Build results
    results = []
    for city in CITIES:
        n  = city["name"]
        bl = baselines.get(n, {})
        mc = match_counts.get(n, {"total": 0, "played": 0})
        g  = GDP_IMPACT.get(n, {})

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
            "matchesTotal":      mc["total"],
            "matchesPlayed":     mc["played"],
            "gdpImpactUsdM":     g.get("impact_usd_m", 0),
            "gdpPctAnnual":      g.get("pct_annual_gdp", 0),
            "metroGdpUsdBn":     g.get("metro_gdp_usd_bn", 0),
            "displacementTier":  g.get("tier", ""),
            "displacementPct":   g.get("displacement_pct", 25),
            "multiplier":        g.get("multiplier", 1.75),
            "beerPriceUsd":      g.get("beer_usd", 0),
            "hotelRateUsd":      g.get("hotel_rate_usd", 0),
            "hotelPremiumPct":   g.get("hotel_premium_pct", 0),
        })

    results.sort(key=lambda x: x["lastWeekCombined"], reverse=True)

    print("\n=== Final Standings ===")
    for i, city in enumerate(results):
        print("  " + city["name"].ljust(25)
              + "  combined=" + str(city["lastWeekCombined"]) + "x"
              + "  pts=" + str(city["lastWeekPts"]))

    now = datetime.now(timezone.utc)
    existing_data2 = {}
    if os.path.exists("data/data.json"):
        try:
            with open("data/data.json") as f:
                existing_data2 = json.load(f)
        except Exception:
            pass

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":          now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay":   now.strftime("%d %b %Y, %H:%Mz"),
            "metric":           "50% stadium Wikipedia + 50% Wikivoyage vs same-period baseline (2019/2022/2023) | GDP impact: modelled visitor spend estimate | Matches: static kickoff-time schedule",
            "baselineYears":    BASELINE_YEARS,
            "baselineWindow":   l7_start + " to " + l7_end + " (equiv. in " + str(BASELINE_YEARS) + ")",
            "baselines":        baselines,
            "cities":           results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Top city: " + results[0]["name"]
          + " (" + str(results[0]["lastWeekCombined"]/100) + "x)")


main()
