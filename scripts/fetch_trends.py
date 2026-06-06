#!/usr/bin/env python3

import json
import time
import os
from datetime import datetime, timezone, date
from pytrends.request import TrendReq

CITIES = [
    {"name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",    "term": "New York World Cup"},
    {"name": "Los Angeles",           "country": "USA", "flag": "US", "region": "West",    "term": "Los Angeles World Cup"},
    {"name": "Dallas",                "country": "USA", "flag": "US", "region": "Central", "term": "Dallas World Cup"},
    {"name": "Mexico City",           "country": "MEX", "flag": "MX", "region": "Central", "term": "Mexico City World Cup"},
    {"name": "Miami",                 "country": "USA", "flag": "US", "region": "East",    "term": "Miami World Cup"},
    {"name": "Atlanta",               "country": "USA", "flag": "US", "region": "Central", "term": "Atlanta World Cup"},
    {"name": "San Francisco",         "country": "USA", "flag": "US", "region": "West",    "term": "San Francisco World Cup"},
    {"name": "Seattle",               "country": "USA", "flag": "US", "region": "West",    "term": "Seattle World Cup"},
    {"name": "Toronto",               "country": "CAN", "flag": "CA", "region": "East",    "term": "Toronto World Cup"},
    {"name": "Boston",                "country": "USA", "flag": "US", "region": "East",    "term": "Boston World Cup"},
    {"name": "Guadalajara",           "country": "MEX", "flag": "MX", "region": "West",    "term": "Guadalajara World Cup"},
    {"name": "Houston",               "country": "USA", "flag": "US", "region": "Central", "term": "Houston World Cup"},
    {"name": "Philadelphia",          "country": "USA", "flag": "US", "region": "East",    "term": "Philadelphia World Cup"},
    {"name": "Vancouver",             "country": "CAN", "flag": "CA", "region": "West",    "term": "Vancouver World Cup"},
    {"name": "Monterrey",             "country": "MEX", "flag": "MX", "region": "Central", "term": "Monterrey World Cup"},
    {"name": "Kansas City",           "country": "USA", "flag": "US", "region": "Central", "term": "Kansas City World Cup"},
]

TOURNAMENT_START = date(2026, 6, 11)


def get_cumulative_timeframe():
    today = date.today()
    if today < TOURNAMENT_START:
        print("  Tournament has not started - using 90-day pre-tournament window")
        return "today 3-m"
    return TOURNAMENT_START.strftime("%Y-%m-%d") + " " + today.strftime("%Y-%m-%d")


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_batch(pytrends, terms, timeframe):
    print("    Terms: " + str(terms))
    print("    Timeframe: " + timeframe)
    pytrends.build_payload(terms, cat=0, timeframe=timeframe, geo="", gprop="")
    df = pytrends.interest_over_time()
    if df.empty:
        print("    Warning: empty dataframe returned")
        return {t: 0 for t in terms}
    result = {}
    for t in terms:
        result[t] = int(round(df[t].mean())) if t in df.columns else 0
        print("    " + t + " -> " + str(result[t]))
    return result


def normalise_cross_batch(batches, all_terms):
    """
    Each batch is normalised internally by Google (max=100).
    To compare across batches we find the highest-scoring term in each batch
    and scale the other batches relative to the first batch's max.
    """
    # Find max score in each batch (excluding isPartial column artifacts)
    batch_maxes = []
    for batch in batches:
        vals = [v for k, v in batch.items() if k in all_terms]
        batch_maxes.append(max(vals) if vals else 1)

    ref_max = batch_maxes[0] or 1
    normalised = {}
    for batch, bmax in zip(batches, batch_maxes):
        scale = ref_max / (bmax or 1)
        for term, score in batch.items():
            if term in all_terms:
                normalised[term] = min(100, int(round(score * scale)))
    return normalised


def fetch_all():
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=2, backoff_factor=2)
    all_terms = [c["term"] for c in CITIES]
    term_batches = list(chunks(all_terms, 5))
    cumul_tf = get_cumulative_timeframe()
    weekly_b = []
    cumul_b = []

    for i, batch in enumerate(term_batches):
        print("\n  Batch " + str(i + 1) + "/" + str(len(term_batches)))
        print("  -> Weekly fetch")
        weekly_b.append(fetch_batch(pytrends, batch, "now 7-d"))
        time.sleep(6)
        print("  -> Cumulative fetch")
        cumul_b.append(fetch_batch(pytrends, batch, cumul_tf))
        time.sleep(6)

    ws = normalise_cross_batch(weekly_b, all_terms)
    cs = normalise_cross_batch(cumul_b, all_terms)

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
    now = datetime.now(timezone.utc)

    print("\nScores:")
    for city in data:
        print("  " + city["name"] + ": week=" + str(city["weekScore"]) + " cumul=" + str(city["cumulative"]))

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":         now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay":  now.strftime("%d %b %Y, %H:%Mz"),
            "tournamentStart": TOURNAMENT_START.strftime("%Y-%m-%d"),
            "anchor":          "none - direct city comparison",
            "cities":          data,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone - top city: " + data[0]["name"] + " (" + str(data[0]["weekScore"]) + ")")


main()
