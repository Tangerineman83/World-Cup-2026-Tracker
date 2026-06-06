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

WEEKS = [
    {"label": "Week 1", "start": "2026-06-11", "end": "2026-06-17"},
    {"label": "Week 2", "start": "2026-06-18", "end": "2026-06-24"},
    {"label": "Week 3", "start": "2026-06-25", "end": "2026-07-01"},
    {"label": "Week 4", "start": "2026-07-02", "end": "2026-07-08"},
]

# Included in every batch as a common reference for cross-batch normalisation.
# This prevents any solo or lightly-contested term from being auto-scored 100.
ANCHOR = "World Cup"


def is_week_available(week):
    return date.today() >= date.fromisoformat(week["start"])


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
            for t, v in result.items():
                print("    " + t + " -> " + str(v))
            return result
        except Exception as e:
            print("    Error: " + str(e))
            continue
    print("    All retries failed - returning zeros")
    return {t: 0 for t in terms}


def fetch_timeframe(pytrends, all_terms, timeframe, label):
    """
    Fetch all 16 city terms in batches of 4, with the ANCHOR appended to every
    batch as the 5th term. The anchor's score in each batch is used to rescale
    all batches onto a common reference, so no city gets an artificially high
    score just because it was alone or in a small batch.
    """
    print("\n  [" + label + "] timeframe: " + timeframe)
    term_batches = list(chunks(all_terms, 4))
    batches = []
    for i, batch in enumerate(term_batches):
        batch_with_anchor = batch + [ANCHOR]
        print("  Batch " + str(i + 1) + "/" + str(len(term_batches)) + ": " + str(batch))
        result = fetch_batch_with_retry(pytrends, batch_with_anchor, timeframe)
        batches.append(result)
        if i < len(term_batches) - 1:
            time.sleep(8)
    return normalise_with_anchor(batches, all_terms)


def normalise_with_anchor(batches, all_terms):
    """
    Two-stage normalisation:

    Stage 1 - Cross-batch alignment using anchor ("World Cup"):
      Each batch is scaled relative to Batch 0 using the anchor's score.
      This corrects for the fact that Google scores each batch independently,
      so a city alone in a batch would otherwise get an artificially high score.

    Stage 2 - Rescale to best city = 100:
      After alignment, scores are expressed as % of the top-scoring city.
      This gives an intuitive 0-100 index where 100 = most interested city
      that week, regardless of how the raw anchor-relative scores were compressed.

    The anchor ("World Cup") is intentionally a much higher-volume term than
    any individual city, so city scores will naturally land in a compressed
    range (e.g. 15-45) before Stage 2 rescaling. That compression is fine -
    it reflects genuine relative interest levels. Stage 2 just re-expresses
    those proportions on a 0-100 scale for readability.
    """
    # Stage 1: align batches using anchor
    ref_anchor = batches[0].get(ANCHOR, 1) or 1
    print("\n  Stage 1 - Anchor alignment (ref anchor score=" + str(ref_anchor) + "):")

    anchor_relative = {}  # city scores as % of World Cup anchor
    for i, batch in enumerate(batches):
        batch_anchor = batch.get(ANCHOR, 1) or 1
        scale = ref_anchor / batch_anchor
        print("    Batch " + str(i + 1) + ": anchor=" + str(batch_anchor) + "  scale=" + str(round(scale, 3)))
        for term, score in batch.items():
            if term in all_terms:
                anchor_relative[term] = round(score * scale, 2)

    print("  Raw anchor-relative scores (compressed range expected):")
    for t, v in sorted(anchor_relative.items(), key=lambda x: x[1], reverse=True):
        print("    " + t + ": " + str(v))

    # Stage 2: rescale so best city = 100
    best_city_score = max(anchor_relative.values()) if anchor_relative else 1
    print("\n  Stage 2 - Rescale to best city (best=" + str(round(best_city_score, 2)) + "):")
    normalised = {}
    for term, score in anchor_relative.items():
        normalised[term] = min(100, int(round(score / best_city_score * 100)))

    print("  Final index scores (top city = 100):")
    for t, v in sorted(normalised.items(), key=lambda x: x[1], reverse=True)[:5]:
        print("    " + t + ": " + str(v))

    return normalised


def scores_to_points(normalised_scores, all_terms):
    """
    1st = 10pts, 2nd = 9pts ... 10th = 1pt, 11th-16th = 0pts.
    """
    ranked = sorted(all_terms, key=lambda t: normalised_scores.get(t, 0), reverse=True)
    points = {}
    for i, term in enumerate(ranked):
        points[term] = max(0, 10 - i)
    return points


def fetch_all():
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(15, 30), retries=3, backoff_factor=2)
    all_terms = [c["term"] for c in CITIES]
    today = date.today()

    # Discrete tournament weeks
    week_data = {}
    for week in WEEKS:
        if today < date.fromisoformat(week["start"]):
            print("\nSkipping " + week["label"] + " (not started yet)")
            continue
        print("\n=== " + week["label"] + " (" + week["start"] + " to " + week["end"] + ") ===")
        tf = week["start"] + " " + week["end"]
        scores = fetch_timeframe(pytrends, all_terms, tf, week["label"])
        week_data[week["label"]] = {
            "scores": scores,
            "points": scores_to_points(scores, all_terms)
        }
        time.sleep(10)

    # Rolling last 7 days
    print("\n=== Last 7 Days (rolling) ===")
    last7_scores = fetch_timeframe(pytrends, all_terms, "now 7-d", "Last 7 days")
    last7_points = scores_to_points(last7_scores, all_terms)

    # Build results
    results = []
    for city in CITIES:
        t = city["term"]
        week_points = {}
        week_scores = {}
        for week in WEEKS:
            lbl = week["label"]
            if lbl in week_data:
                week_points[lbl] = week_data[lbl]["points"].get(t, 0)
                week_scores[lbl] = week_data[lbl]["scores"].get(t, 0)
            else:
                week_points[lbl] = None
                week_scores[lbl] = None

        to_date = sum(v for v in week_points.values() if v is not None)

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
            "toDatePoints":  to_date,
        })

    results.sort(key=lambda x: (x["toDatePoints"], x["lastWeekPts"]), reverse=True)

    print("\n=== Final Standings ===")
    for city in results:
        print("  " + city["name"].ljust(25) +
              "  last7idx=" + str(city["lastWeekScore"]).rjust(3) +
              "  last7pts=" + str(city["lastWeekPts"]).rjust(2) +
              "  toDate=" + str(city["toDatePoints"]).rjust(3))

    return results


def main():
    print("Fetching Google Trends for 16 World Cup host cities...")
    print("Anchor term: '" + ANCHOR + "' (high-volume benchmark)")
    data = fetch_all()
    now = datetime.now(timezone.utc)

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated":        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updatedDisplay": now.strftime("%d %b %Y, %H:%Mz"),
            "weeks":          WEEKS,
            "cities":         data,
        }, f, ensure_ascii=False, indent=2)

    print("\nDone. Written to data/data.json")
    print("Top city (last 7 days): " + data[0]["name"])


main()
