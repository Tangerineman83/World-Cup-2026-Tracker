#!/usr/bin/env python3

import json
import time
import os
from datetime import datetime, timezone, date
from pytrends.request import TrendReq

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

# Tournament week windows - Sunday to Saturday to align with Google Trends weekly data
WEEKS = [
    {"label": "Week 1", "start": "2026-06-11", "end": "2026-06-17"},
    {"label": "Week 2", "start": "2026-06-18", "end": "2026-06-24"},
    {"label": "Week 3", "start": "2026-06-25", "end": "2026-07-01"},
    {"label": "Week 4", "start": "2026-07-02", "end": "2026-07-08"},
]


def is_week_available(week):
    """Only fetch a week if its start date has passed."""
    today = date.today()
    return today >= date.fromisoformat(week["start"])


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_batch_with_retry(pytrends, terms, timeframe, max_retries=3):
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 15 * attempt
            print("    Retry " + str(attempt) + " after " + str(wait) + "s...")
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
            values = list(result.values())
            if max(values) if values else 0 <= 1:
                print("    Scores too low (max=" + str(max(values) if values else 0) + ") - retrying")
                continue
            for t, v in result.items():
                print("    " + t + " -> " + str(v))
            return result
        except Exception as e:
            print("    Error: " + str(e))
            continue
    print("    All retries failed - returning zeros")
    return {t: 0 for t in terms}


def fetch_timeframe(pytrends, all_terms, timeframe, label):
    print("\n  [" + label + "] timeframe: " + timeframe)
    term_batches = list(chunks(all_terms, 5))
    batches = []
    for i, batch in enumerate(term_batches):
        print("  Batch " + str(i + 1) + "/" + str(len(term_batches)))
        batches.append(fetch_batch_with_retry(pytrends, batch, timeframe))
        if i < len(term_batches) - 1:
            time.sleep(8)
    return normalise_across_batches(batches, all_terms)


def normalise_across_batches(batches, all_terms):
    global_max = 1
    for batch in batches:
        for term, score in batch.items():
            if term in all_terms and score > global_max:
                global_max = score
    normalised = {}
    for batch in batches:
        for term, score in batch.items():
            if term in all_terms:
                normalised[term] = int(round(score / global_max * 100))
    return normalised


def scores_to_points(normalised_scores, all_terms):
    """
    Convert normalised interest scores into weekly points.
    1st = 16pts, 2nd = 15pts ... 16th = 1pt
    (Using 16 cities so points run 16 down to 1)
    """
    ranked = sorted(all_terms, key=lambda t: normalised_scores.get(t, 0), reverse=True)
    points = {}
    total = len(all_terms)
    for i, term in enumerate(ranked):
        points[term] = total - i  # 16 for 1st, 15 for 2nd ... 1 for 16th
    return points


def main():
    print("Fetching Google Trends data for 16 World Cup host cities...")
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(15, 30), retries=3, backoff_factor=2)
    all_terms = [c["term"] for c in CITIES]
    now = datetime.now(timezone.utc)
    today = date.today()

    # --- Fetch each discrete week that has started ---
    week_data = {}
    for week in WEEKS:
        if not is_week_available(week):
            print("\nSkipping " + week["label"] + " (not started yet)")
            continue
        print("\n=== " + week["label"] + " (" + week["start"] + " to " + week["end"] + ") ===")
        tf = week["start"] + " " + week["end"]
        scores = fetch_timeframe(pytrends, all_terms, tf, week["label"])
        points = scores_to_points(scores, all_terms)
        week_data[week["label"]] = {"scores": scores, "points": points}
        time.sleep(10)

    # --- Fetch last 7 days (rolling) ---
    print("\n=== Last 7 days (rolling) ===")
    last7_scores = fetch_timeframe(pytrends, all_terms, "now 7-d", "Last 7 days")
    last7_points = scores_to_points(last7_scores, all_terms)

    # --- Build results ---
    results = []
    for city in CITIES:
        t = city["term"]

        # Points per discrete week
        week_points = {}
        week_scores = {}
        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                week_points[lbl] = week_data[lbl]["points"].get(t, 0)
                week_scores[lbl] = week_data[lbl]["scores"].get(t, 0)
            else:
                week_points[lbl] = None  # not yet available
                week_scores[lbl] = None

        # To date = sum of all available discrete week points
        to_date_points = sum(v for v in week_points.values() if v is not None)

        results.append({
            "name":          city["name"],
            "country":       city["country"],
            "flag":          city["flag"],
            "region":        city["region"],
            "term":          t,
            "trendsUrl":     "https://trends.google.com/trends/explore?q=" + t.replace(" ", "+") + "&date=now+7-d",
            "lastWeekScore": last7_scores.get(t, 0),
            "lastWeekPts":   last7_points.get(t, 0),
            "weekPoints":    week_points,
            "weekScores":    week_scores,
            "toDatePoints":  to_date_points,
        })

    # Default sort by to-date points (or last week if no weeks available yet)
    results.sort(key=lambda x: (x["toDatePoints"], x["lastWeekPts"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25) +
              " last7pts=" + str(city["lastWeekPts"]).rjust(2) +
              " toDate=" + str(city["toDatePoints"]).rjust(3))

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "weeks":          WEEKS,
            "cities":         results,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")


main()
