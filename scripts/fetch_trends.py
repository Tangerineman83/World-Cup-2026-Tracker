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
    {"name": "Vancouver",             "country": "CAN", "flag": "🇨", "region": "West",    "term": "Vancouver World Cup 2026"},
    {"name": "Monterrey",             "country": "MEX", "flag": "🇲🇽", "region": "Central", "term": "Monterrey World
