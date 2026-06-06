#!/usr/bin/env python3
"""
fetch_trends.py
Fetches Google Trends interest data for all 16 FIFA World Cup 2026 host cities
and writes the result to data/data.json for the static site to consume.

Uses a multi-batch approach with an anchor term to normalise scores across
batches (pytrends has a hard limit of 5 keywords per request).
"""

import json
import time
import os
from datetime import datetime, timezone
from pytrends.request import TrendReq

# ── Config ─────────────────────────────────────────────────────────────────────

CITIES = [
    {"name": "New York / New Jersey", "country": "USA", "flag": "🇺🇸", "region": "East",    "term": "New York World Cup 2026"},
    {"name": "Los Angeles",           "country": "USA", "flag": "🇺🇸", "region": "West",    "term": "Los Angeles World Cup 2026"},
    {"name": "Dallas",                "country": "USA", "flag": "🇺🇸", "region": "Central", "term": "Dallas World Cup 2026"},
    {"name": "Mexico City",           "country": "MEX", "flag": "🇲🇽", "region": "Central", "term": "Mexico City World Cup 2026"},
    {"name": "Miami",                 "country": "USA", "flag": "🇺🇸", "region": "East",    "term": "Miami World Cup 2026"},
    {"name": "Atlanta",               "country": "USA", "flag": "🇺🇸", "region": "Central", "term": "Atlanta World Cup 2026"},
    {"name": "San Francisco",         "country": "USA", "flag": "🇺🇸", "region": "West",    "term": "San Francisco World Cup 2026"},
    {"name": "Seattle",               "country": "USA", "flag": "🇺🇸", "region": "West",    "term": "Seattle World Cup 2026"},
    {"name": "Toronto",               "country": "CAN", "flag": "🇨🇦", "region": "East",    "term": "Toronto World Cup 2026"},
    {"name": "Boston",                "country": "USA", "flag": "🇺🇸", "region": "East",    "term": "Boston World Cup 2026"},
    {"name": "Guadalajara",           "country": "MEX", "flag": "🇲🇽", "region": "West",    "term": "Guadalajara World Cup 2026"},
    {"name": "Houston",               "country": "USA", "flag": "🇺🇸", "region": "Central", "term": "Houston World Cup 2026"},
    {"name": "Philadelphia",          "country": "USA", "flag": "🇺🇸", "region": "East",    "term": "Philadelphia World Cup 2026"},
    {"name": "Vancouver",             "country": "CAN", "flag": "🇨🇦", "region": "West",    "term": "Vancouver World Cup 2026"},
    {"name": "Monterrey",             "country": "MEX", "flag": "🇲🇽", "region": "Central", "term": "Monterrey World Cup 2026"},
    {"name": "Kansas City",           "country": "USA", "flag": "🇺🇸", "region": "Central", "term": "Kansas City World Cup 2026"},
]

# Anchor term included in every batch so scores can be cross-normalised
ANCHOR = "FIFA World Cup 2026"

# Tournament start date (used to decide cumulative window)
TOURNAMENT_START = "2026-06-11"

# ── Helpers ────────────────────────────────────────────────────────────────────

def chunks(lst, n):
    """Split list into chunks of at most n items."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def fetch_batch(pytrends, terms, timeframe):
    """Fetch a single batch and return a dict of term -> average interest."""
    pytrends.build_payload(terms, cat=20, timeframe=timeframe, geo="", gprop="")
    df = pytrends.interest_over_time()
    if df.empty:
        return {t: 0 for t in terms}
    results = {}
    for term in terms:
        if term in df.columns:
            results[term] = int(round(df[term].mean()))
        else:
            results[term] = 0
    return results

def normalise_batches(batches_with_anchor, anchor_term):
    """
    Each batch contains the anchor term. We use the anchor's score in each
    batch to scale all other scores relative to batch 0, so all 16 cities
    end up on the same 0-100 scale.
    """
    # Find the anchor score in the first batch as reference
    ref_anchor = batches_with_anchor[0].get(anchor_term, 1) or 1
    normalised = {}
    for batch in batches_with_anchor:
        batch_anchor = batch.get(anchor_term, 1) or 1
        scale = ref_anchor / batch_anchor
        for term, score in batch.items():
            if term != anchor_term:
                normalised[term] = min(100, int(round(score * scale)))
    return normalised

# ── Main fetch ─────────────────────────────────────────────────────────────────

def fetch_all():
    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25), retries=3, backoff_factor=1.5)

    all_terms = [c["term"] for c in CITIES]
    # Split into batches of 4 (leaving 1 slot for anchor)
    term_batches = list(chunks(all_terms, 4))

    weekly_batches = []
    cumulative_batches = []

    for i, batch in enumerate(term_batches):
        batch_with_anchor = batch + [ANCHOR]
        print(f"  Fetching batch {i+1}/{len(term_batches)}: {batch}")

        # Weekly (last 7 days)
        weekly = fetch_batch(pytrends, batch_with_anchor, "now 7-d")
        weekly_batches.append(weekly)
        time.sleep(3)  # be polite to Google

        # Cumulative (tournament start → now)
        cumul = fetch_batch(pytrends, batch_with_anchor, f"{TOURNAMENT_START} {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        cumulative_batches.append(cumul)
        time.sleep(3)

    weekly_scores   = normalise_batches(weekly_batches,     ANCHOR)
    cumulative_scores = normalise_batches(cumulative_batches, ANCHOR)

    results = []
    for city in CITIES:
        t = city["term"]
        results.append({
            **city,
            "weekScore":   weekly_scores.get(t, 0),
            "cumulative":  cumulative_scores.get(t, 0),
            "trendsUrl":   f"https://trends.google.com/trends/explore?q={t.replace(' ', '+')}&date=now+7-d",
        })

    # Sort by weekly score descending
    results.sort(key=lambda x: x["weekScore"], reverse=True)

    return results

# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("Fetching Google Trends data for 16 World Cup host cities…")
    data = fetch_all()

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedDisplay": datetime.now(timezone.utc).strftime("%-d %b %Y, %H:%Mz"),
        "tournamentStart": TOURNAMENT_START,
        "anchor": ANCHOR,
        "cities": data,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Written data/data.json with {len(data)} cities")
    print(f"  Top city this week: {data[0]['name']} ({data[0]['weekScore']})")

if __name__ == "__main__":
    main()
