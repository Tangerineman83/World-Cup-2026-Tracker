#!/usr/bin/env python3
"""
fetch_trends.py
Fetches Google Trends interest data for all 16 FIFA World Cup 2026 host cities
and writes the result to data/data.json for the static site to consume.
"""

import json
import time
import os
from datetime import datetime, timezone, date
from pytrends.request import TrendReq

# ── Config ─────────────────────────────────────────────────────────────────────

CITIES = [
    {"name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",    "term": "New York World Cup 2026"},
    {"name": "Los Angeles",           "country": "USA", "flag": "US", "region": "West",    "term": "Los Angeles World Cup 2026"},
    {"name": "Dallas",                "country": "USA", "flag": "US", "region": "Central", "term": "Dallas World Cup 2026"},
    {"name": "Mexico City",           "country": "MEX", "flag": "MX", "region": "Central", "term": "Mexico City World Cup 2026"},
    {"name": "Miami",                 "country": "USA", "flag": "US", "region": "East",    "term": "Miami World Cup 2026"},
    {"name": "Atlanta",               "country": "USA", "flag": "US", "region": "Central", "term": "Atlanta World Cup 2026"},
    {"name": "San Francisco",         "country": "USA", "flag": "US", "region": "West",    "term": "San Francisco World Cup 2026"},
    {"name": "Seattle",               "country": "USA", "flag": "US", "region": "West",    "term": "Seattle World Cup 2026"},
    {"name": "Toronto",               "country": "CAN", "flag": "CA", "region": "East",    "term": "Toronto World Cup 2026"},
    {"name": "Boston",                "country": "USA", "flag": "US", "region": "East",    "term": "Boston World Cup 2026"},
    {"name": "Guadalajara",           "country": "MEX", "flag": "MX", "region": "West",    "term": "Guadalajara World Cup 2026"},
    {"name": "Houston",               "country": "USA", "flag": "US", "region": "Central", "term": "Houston World Cup 2026"},
    {"name": "Philadelphia",          "country": "USA", "flag": "US", "region": "East",    "term": "Philadelphia World Cup 2026"},
    {"name": "Vancouver",             "country": "CAN", "flag": "CA", "region": "West",    "term": "Vancouver World Cup 2026"},
    {"name": "Monterrey",             "country": "MEX", "flag": "MX", "region": "Central", "term": "Monterrey World Cup 2026"},
    {"name": "Kansas City",           "country": "USA", "flag": "US", "region": "Central", "term": "Kansas City World Cup 2026"},
]

ANCHOR           = "FIFA World Cup 2026"
TOURNAMENT_START = date(2026, 6, 11)

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_cumulative_timeframe():
    today = date.today()
    if today < TOURNAMENT_START:
        print("  Tournament has not started yet - using 90-day pre-tournament window")
        return "today 3-m"
    else:
        return TOURNAMENT_START.strftime("%Y-%m-%d") + " " + today.strftime("%Y-%m-%d")

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def fetch_batch(pytrends, terms, timeframe):
    print("    Timeframe: " + timeframe)
    pytrends.build_payload(terms, cat=0, timeframe=timeframe, geo="", gprop="")
    df = pytrends.interest_over_time()
    if df.empty:
        print("    Warning: empty dataframe for " + str(terms))
        return {t: 0 for t in terms}
    return {t: int(round(df[t].mean())) if t in df.columns else 0 for t in terms}

def normalise_batches(batches, anchor_term):
    ref = batches[0].get(anchor_term, 1) or 1
    normalised = {}
    for batch in batches:
        scale = ref / (batch.get(anchor_term, 1) or 1)
        for term, score in batch.items():
            if term != anchor_term:
                normalised[term] = min(100, int(round(score * scale)))
    return normalised

# ── Main ───────────────────────────────────────────────────────────────────────

def fetch_all():
    pytrends     = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=2, backoff_factor=2)
    term_batches = list(chunks([c["term"] for c in CITIES], 4))
    cumul_tf     = get_cumulative_timeframe()
    weekly_b     = []
    cumul_b      = []

    for i, batch in enumerate(term_batches):
        bwa = batch + [ANCHOR]
        print("\n  Batch " + str(i+1) + "/" + str(len(term_batches)) + ": " + str(batch))
        print("  -> Weekly")
        weekly_b.append(fetch_batch(pytrends, bwa, "now 7-d"))
        time.sleep(5)
        print("  -> Cumulative")
        cumul_b.append(fetch_batch(pytrends, bwa, cumul_tf))
        time.sleep(5)

    ws = normalise_batches(weekly_b, ANCHOR)
    cs = normalise_batches(cumul_b,  ANCHOR)

    results = []
    for city in CITIES:
        t = city["term"]
        results.append({
            "name":       city["name"],
            "country":    city["country"],
            "flag":       city["flag"],
            "region":     city["region"],
            "term":       t,
            "weekScore":  ws.get(t, 0),
            "cumulative": cs.get(t, 0),
            "trendsUrl":  "https://trends.google.com/trends/explore?q=" + t.replace(" ", "+") + "&date=now+7-d",
        })

    return sorted(results, key=lambda x: x["weekScore"], reverse=True)

def main():
    print("Fetching Google Trends data for 16 World Cup host cities...")
    data = fetch_all()
    now  = datetime.now(timezone.utc)

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":         now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay":  now.strftime("%d %b %Y, %H:%Mz"),
            "tournamentStart": TOURNAMENT_START.strftime("%Y-%m-%d"),
            "anchor":          ANCHOR,
            "cities":          data,
        }, f, ensure_ascii=False, indent=2)

    print("\nWritten data/data.json - top city: " + data[0]["name"] + " (" + str(data[0]["weekScore"]) + ")")

if __name__ == "__main__":
