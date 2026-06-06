#!/usr/bin/env python3

import json
import time
import os
from datetime import datetime, timezone, date
from pytrends.request import TrendReq

# Search terms matched to what people actually search on Google Trends
CITIES = [
    {"name": "New York / New Jersey", "country": "USA", "flag": "US", "region": "East",    "term": "New Jersey World Cup"},
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


def fetch_batch_with_retry(pytrends, terms, timeframe, max_retries=3):
    """Fetch with retries and validate we got real data, not zeros."""
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 15 * attempt
            print("    Retry " + str(attempt) + " after " + str(wait) + "s wait...")
            time.sleep(wait)
        try:
            pytrends.build_payload(terms, cat=0, timeframe=timeframe, geo="", gprop="")
            df = pytrends.interest_over_time()

            if df.empty:
                print("    Empty dataframe on attempt " + str(attempt + 1))
                continue

            result = {}
            for t in terms:
                result[t] = int(round(df[t].mean())) if t in df.columns else 0

            # Check we got real data - if all zeros or all ones, something went wrong
            values = list(result.values())
            max_val = max(values) if values else 0
            if max_val <= 1:
                print("    Suspiciously low scores (max=" + str(max_val) + ") on attempt " + str(attempt + 1) + " - retrying")
                continue

            for t, v in result.items():
                print("    " + t + " -> " + str(v))
            return result

        except Exception as e:
            print("    Error on attempt " + str(attempt + 1) + ": " + str(e))
            continue

    # If all retries failed, return zeros
    print("    All retries failed - returning zeros for this batch")
    return {t: 0 for t in terms}


def normalise_across_batches(batches, all_terms):
    """
    Google scores each batch independently with max=100.
    To put all 16 cities on the same scale, find the global max across
    all batches and scale everything relative to that.
    """
    # Find the single highest score across all batches
    global_max = 1
    for batch in batches:
        for term, score in batch.items():
            if term in all_terms and score > global_max:
                global_max = score

    print("\n  Global max score across all batches: " + str(global_max))

    normalised = {}
    for batch in batches:
        for term, score in batch.items():
            if term in all_terms:
                normalised[term] = int(round(score / global_max * 100))

    return normalised


def fetch_all():
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(15, 30), retries=3, backoff_factor=2)
    all_terms = [c["term"] for c in CITIES]
    # Batch size 5 = pytrends max, gives us 4 batches for 16 cities
    term_batches = list(chunks(all_terms, 5))
    cumul_tf = get_cumulative_timeframe()
    weekly_b = []
    cumul_b = []

    for i, batch in enumerate(term_batches):
        print("\n  === Batch " + str(i + 1) + "/" + str(len(term_batches)) + " ===")
        print("  Terms: " + str(batch))

        print("  -> Weekly (now 7-d)")
        weekly_b.append(fetch_batch_with_retry(pytrends, batch, "now 7-d"))
        time.sleep(8)

        print("  -> Cumulative (" + cumul_tf + ")")
        cumul_b.append(fetch_batch_with_retry(pytrends, batch, cumul_tf))
        time.sleep(8)

    ws = normalise_across_batches(weekly_b, all_terms)
    cs = normalise_across_batches(cumul_b, all_terms)

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

    print("\n=== Final Scores ===")
    for city in data:
        print("  " + city["name"].ljust(25) + " week=" + str(city["weekScore"]).rjust(3) + "  cumul=" + str(city["cumulative"]).rjust(3))

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":         now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay":  now.strftime("%d %b %Y, %H:%Mz"),
            "tournamentStart": TOURNAMENT_START.strftime("%Y-%m-%d"),
            "cities":          data,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")
    print("Top city: " + data[0]["name"] + " (" + str(data[0]["weekScore"]) + ")")


main()
