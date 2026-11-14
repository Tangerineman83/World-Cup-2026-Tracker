# World-Cup-2026-Tracker: model methodology (replication grade)

- **Repo:** `Tangerineman83/World-Cup-2026-Tracker` (public). Read at HEAD `c444b6c` (14 Nov 2026 15:09 UK, an automated "chore: update pageviews data" commit).
- **Read method:** a read-only local clone at `/workspace/modelling/methods/_clones/World-Cup-2026-Tracker`, with the push URL set to `DISABLED`. Nothing in the repo was changed.
- **Written:** 14 Nov 2026 (Europe/London) for job t177u.
- **Citations:** `file:line` refers to HEAD `c444b6c`. Every parameter value below is quoted from code or committed data. Where a value is not in the repo, it says **not specified in repo**.

---

## 1. Purpose

A public GitHub Pages tracker for the 16 host cities of the 2026 FIFA World Cup. It has two distinct models:

| Model | Status | Files |
|---|---|---|
| **Pageview uplift tracker** (live) | A scheduled Action runs `scripts/fetch_trends.py` twice daily and commits `data/data.json`. The site (`index.html`) draws a ranking from that file. | `scripts/fetch_trends.py`, `.github/workflows/fetch-trends.yml`, `data/data.json` |
| **Visitor-spend GDP impact** (static) | A one-off, city-level estimate of incremental tourist spending, disclosed in `assumptions.html`. The resulting dollars and percentages are **hard-coded** in `GDP_IMPACT` inside `fetch_trends.py` and are copied into `data.json`. They are not recomputed when the Action runs. | `assumptions.html` (method), `fetch_trends.py:188-205` (committed numbers) |

This is not a match-outcome model (that lives in `World-Cup-Odds`). It does not predict winners.

---

## 2. Data sources (with dates)

### 2.1 Pageview tracker

| Data | Source / URL | Date / vintage | Where |
|---|---|---|---|
| English Wikipedia stadium pageviews | Wikimedia REST: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}` (`fetch_trends.py:110-114`) | Fetched at each run, last-7-day window | `data/data.json` |
| English Wikivoyage city pageviews | Same API, project `en.wikivoyage` | Same | `data/data.json` |
| Baseline years | Same calendar 7-day window, averaged across **2019, 2022, 2023** (comment: "no Copa America, Club WC, or COVID in Jun-Jul window") | Those three years | `BASELINE_YEARS`, `:86-87` and again `:207-209` |
| Match schedule (for "matches played") | Static `CITY_MATCH_KICKOFFS` in the same script. The assumptions page says kickoff times come from the official 104-match schedule via kickoffclock.com. | Confirmed through the Final on 19 Jul 2026, per `assumptions.html` | `fetch_trends.py` `get_match_counts` `:254-275`; a match is "played" at kickoff + 2.5 hours UTC (`MATCH_DURATION_BUFFER`, just above `:254`) |

City Wikipedia pageviews were tried and **removed** (comment: "added noise, not signal", `:89`).

### 2.2 GDP impact (method in `assumptions.html`, numbers in `GDP_IMPACT`)

Sources named on the assumptions page (not all of them are stored as files in the repo):

- FIFA official stadium capacities (Oct 2025) and FIFA 2022 attendance surveys for the 25% international / 35% domestic-away split.
- LendingTree Fan Cost Analysis (April 2026) for a $390/day international-spend anchor; Numbeo Restaurant Price Index (June 2026) for city cost-of-living factors; GiveMeSport/SeatPick beer prices; Lighthouse hotel rate data (January 2026) for match-night premiums; CoStar / Front Office Sports and AHLA (June 2026).
- Displacement literature: Zimbalist & Matheson Super Bowl studies; FIFA 2014 Brazil secondary cities; UK Sport/DCMS framework.
- Multipliers: Deloitte Canada Sport Business Advisory (2024), $1.09 per dollar, as the Canadian anchor; Tourism Economics / Oxford Economics / World Bank guidance.
- Metro GDP: US BEA MSA (2023 actuals grown to a 2025 estimate — the growth rates are **not specified in repo**); Statistics Canada CMA converted at **USD 0.72 per CAD**; Mexico INEGI converted at **MXN 17.5 per USD**.
- Comparison totals: FIFA/WTO/OpenEconomics socioeconomic impact analysis, March 2025 ($22.3bn headline; tourist-spend component described as about $5–6bn).

The raw worksheets behind `GDP_IMPACT` are **not in the repo**. Only the finished per-city table is.

---

## 3. Model equations and parameters

### 3.1 Pageview uplift (`fetch_trends.py`)

For a series with views \(V\) in the last 7 days and a baseline average weekly count \(B\) over the same window in 2019/2022/2023:

\[
u = \mathrm{round}\big((V / f) / B \times 100,\ 1\big)
\]

(`uplift`, `:151-155`), with week fraction \(f=1\) in the live "last week only" path. Missing baseline ⇒ \(u=0\).

**Stadium series** is then floored at 100 (i.e. 1.0×):

```python
su = max(su, 100.0) if su > 0 else 100.0   # :448
```

The `else 100.0` branch means a **zero or failed fetch is also written as 1.0×**, not as missing. The file header (`:9`) says this is to stop transient API failures collapsing the ranking.

**Wikivoyage** is clamped (`clamp_wikivoyage`, `:158-166`):

| Parameter | Value | Location |
|---|---|---|
| Floor | 100 (1.0×) | `WIKIVOYAGE_FLOOR`, `:94` |
| Cap | 1000 (10.0×) | `WIKIVOYAGE_CAP`, `:95` |
| Low-confidence cap | 500 (5.0×) if baseline weekly views < 150 | `WIKIVOYAGE_LOW_CONF`, `:96` |

Combined city score (`:169-171`):

\[
C = \mathrm{round}(0.50\,u_{\text{stadium}} + 0.50\,u_{\text{voyage}},\ 1).
\]

Ranking points (`to_points`, `:174-179`): first place 10, second 9, … tenth 1, 11th–16th 0. If every score is 0, all points are 0. Ties are not broken explicitly; `sorted(..., reverse=True)` keeps whichever order the dict happens to have.

These constants are **duplicated** in the same file (`:85-98` and `:207-218`).

### 3.2 Visitor-spend GDP impact (`assumptions.html` "The Formula")

The page states the same five steps for every city. The script does not implement this formula: it stores the finished `impact_usd_m` and `pct_annual_gdp`. A replication should recompute from the steps below and then compare to the hard-coded table.

**Step 1 — fans per match** (locals are excluded):

\[
N_{\text{intl}} = \mathrm{capacity}\times 0.95\times 0.25,\qquad
N_{\text{dom}} = \mathrm{capacity}\times 0.95\times 0.35.
\]

Occupancy 95% is described as "FIFA's own attendance projection". International share 25%, domestic-away 35%, local 40%.

**Step 2 — spend.** International daily spend is a city-adjusted rate in the range **$285–$437**, around a **$390/day** base, times a Numbeo cost-of-living factor (NY = 1.0). A **+20%** "World Cup premium" is applied "on top of the city's normal cost level". Domestic daily spend is **35%** of the international rate. Trip length is **4 days** (FIFA 2022 average 4.2, rounded down). Ticket revenue is excluded (it goes to FIFA). A separate **hotel match-night premium** (2% to 104% by city, from Lighthouse) is added.

The exact algebra that turns `(intl_daily, col_factor, 20% premium, 4 days, hotel_premium, beer price)` into a dollar total is described in prose, not as a single committed expression. Several of those ingredients are stored on each `GDP_IMPACT` row (`capacity`, `intl_per_match`, `domestic_per_match`, `col_factor`, `intl_daily`, `beer_usd`, `hotel_rate_usd`, `hotel_premium_pct`), which is enough to attempt a reconstruction, but the hotel-premium *quantity* (room-nights) is **not specified in repo**.

**Step 3 — displacement.** Incremental spend = total spend × (1 − displacement rate).

| Tier | Displacement | Cities (from the table / `GDP_IMPACT`) |
|---|---:|---|
| Global Gateway | 35% | New York / New Jersey, Los Angeles, Miami, Mexico City, Vancouver |
| Major Regional Hub | 25% | Boston, Seattle, Houston, San Francisco, Toronto |
| Mid-tier Host | 15% | Atlanta, Dallas, Philadelphia |
| Low-tourism City | 8% | Monterrey, Kansas City, Guadalajara |

**Step 4 — multiplier.** Incremental spend × city multiplier, range **1.10× to 1.85×** (New York 1.85; Vancouver 1.10; Toronto 1.15; Mexican cities 1.25–1.40; most US mid-tier 1.65).

**Step 5.** \(\%\text{ of GDP} = \text{impact} / \text{metro GDP}\times 100\).

The committed city results (`fetch_trends.py:188-205`) sum to **$5.691bn**, reported as **$5.7bn**. Country split on the assumptions page: USA $4.7bn (82%), Mexico $0.6bn (11%), Canada $0.4bn (7%). Sensitivity quoted on the page (not coded): 90% occupancy / higher displacement / lower multiplier → **$4.4bn**; 98% occupancy / lower displacement / higher multiplier → **$7.0bn**. A 10 percentage-point change in displacement is said to move the total by about 13%.

Per-city committed figures (impact $m, % of annual GDP, metro GDP $bn, multiplier):

| City | $m | % GDP | GDP $bn | Mult. | Displacement |
|---|---:|---:|---:|---:|---:|
| Monterrey | 224 | 0.264 | 85 | 1.25 | 8% |
| Kansas City | 414 | 0.230 | 180 | 1.55 | 8% |
| Guadalajara | 151 | 0.222 | 68 | 1.30 | 8% |
| Vancouver | 239 | 0.184 | 130 | 1.10 | 35% |
| Atlanta | 469 | 0.104 | 450 | 1.65 | 15% |
| Boston | 492 | 0.093 | 530 | 1.80 | 25% |
| Seattle | 366 | 0.083 | 440 | 1.75 | 25% |
| Miami | 354 | 0.082 | 430 | 1.75 | 35% |
| Dallas | 634 | 0.078 | 815 | 1.65 | 15% |
| Philadelphia | 311 | 0.063 | 490 | 1.65 | 15% |
| Mexico City | 245 | 0.058 | 420 | 1.40 | 35% |
| Houston | 323 | 0.058 | 560 | 1.65 | 25% |
| San Francisco | 369 | 0.051 | 720 | 1.80 | 25% |
| Toronto | 145 | 0.045 | 320 | 1.15 | 25% |
| Los Angeles | 398 | 0.035 | 1,150 | 1.80 | 35% |
| New York / New Jersey | 557 | 0.027 | 2,100 | 1.85 | 35% |

A prose line on the assumptions page says New York is "0.03%"; the table and the code say 0.027%.

The model "treats every match the same" (no knockout vs group mix, no fixture attractiveness). Multi-city trips are counted as incremental in each city. Local resident displacement of their own spend is assumed to cancel. FIFA operational spend, infrastructure, and supply-chain effects are deliberately out of scope (that is why $5.7bn is far below FIFA's $22.3bn headline).

---

## 4. Calibration method

**Pageview weights (50/50) and clamps:** author judgement, after dropping city-Wikipedia as noisy. No in-repo study of the weights.

**GDP parameters:** compiled from the published sources in §2.2. There is no script that turns those sources into `GDP_IMPACT`. Occupancy, visitor mix, 4-day stay, 20% premium, 35% domestic-spend ratio, displacement tiers and multipliers are stated as assumptions, not estimated inside the repo.

---

## 5. Simulation steps, RNG and seeding

No random numbers.

**Live pipeline** (`.github/workflows/fetch-trends.yml`): cron `15 8 * * *` and `15 23 * * *` UTC, plus `workflow_dispatch`. Python 3.11, `requests` is installed but the script uses `urllib`. `fetch_trends.py` `main()` loads or fetches baselines, fetches the last 7 days, applies the uplift rules, attaches the static `GDP_IMPACT` and `get_match_counts()`, and writes `data/data.json`. The workflow commits only if that file changed.

Baselines are cached in the existing `data.json` when the 7-day window has not moved (`load_baselines`). User-Agent: `WC2026UpliftTracker/1.0 (public research; github.com/tracker)` (`:98`). Retries: 4, with 5×2^attempt seconds on HTTP 429 (`:103-136`). A 1.0s sleep sits between city requests (`:333-334`).

---

## 6. Checks run for this doc

- Read `uplift`, `clamp_wikivoyage`, `combined`, `to_points`, the stadium floor at `:448`, and the `GDP_IMPACT` table.
- Summed `impact_usd_m` over 16 cities: 224+414+151+239+469+492+366+354+634+311+245+323+369+145+398+557 = **5,691**, i.e. $5.691bn, consistent with the $5.7bn headline.
- Checked 557 / 2100e3 × 100 = 0.0265%, reported as 0.027%.
- No Action was triggered. No Wikimedia calls were made from this pass.

---

## 7. Outputs

| File / view | Content |
|---|---|
| `data/data.json` | Per-city last-week views, baselines, uplifts, combined score, points, low-confidence flags, plus the static GDP fields and match counts |
| `index.html` | Ranking UI |
| `assumptions.html` | Reader-facing GDP methodology, sensitivity, FIFA comparison, source list |

---

## 8. Validation present

- **Unit or regression tests: none.**
- The workflow has no numeric gate (any change to `data.json` is committed).
- The assumptions page compares $5.7bn with FIFA's tourist-spend band (~$5–6bn) and quotes early 2026 attendance (Azteca, Guadalajara) as a check on the 95% occupancy assumption. Those checks are narrative, not coded.
- The GDP formula is not re-run against the hard-coded table, so a drift between the prose and the numbers would not be caught.

---

## 9. Known limits and bugs noticed

1. **Stadium floor writes 1.0× on a failed or zero fetch** (`su = … else 100.0`). A city whose Wikipedia call failed looks like "exactly at baseline", which can hold or inflate its rank.
2. **GDP impact is frozen.** The five-step formula lives only in HTML. Hotel room-nights are not in the repo, so a bit-exact reconstruction of each $m figure may not be possible from committed inputs alone. Totals do not change as matches are played.
3. **Minor inconsistencies:** New York "0.03%" in prose vs 0.027% in the table; constant blocks are duplicated in `fetch_trends.py`; `to_points` has no tie-break.
4. **Simplifications (disclosed):** one visitor mix for every match; multi-city trips counted in full in each city; locals' spend excluded rather than modelled; ticket revenue excluded.
5. No tests. Baseline-year choice and 50/50 weights are judgement.

---

## 10. Reusable methods

### 10.1 Baseline uplift index

**What it is.** A short-window activity series is expressed as a percentage of the same calendar window in chosen baseline years: \(u=\mathrm{round}((V/f)/B\times 100, 1)\). Here Wikipedia stadium views and Wikivoyage city views, baselines 2019/2022/2023, are averaged 50/50 after clamps.

**Where else it applies.** Any “is this unusual?” tracker: search interest, footfall, pageviews, or (in a markets setting) a return relative to a seasonal baseline. It is not a forecasting model and it is not the World-Cup-Odds match engine.

**Known pitfalls.** The stadium series is floored at 100 even when the fetch is zero or failed, so a missing observation looks like “exactly at baseline”. Wikivoyage is capped at 10× (5× if the baseline is under 150 views/week). Weights and clamps are judgement, not estimated. `to_points` has no tie-break. Constant blocks are duplicated in `fetch_trends.py`.

### 10.2 Clamps and floors on noisy public data

**What it is.** Hard floors, caps, and a low-confidence cap, plus a retry/backoff around the Wikimedia API, to stop a single bad week collapsing the ranking.

**Where else it applies.** The same defensive pattern appears in World-Cup-Odds (margin cap of 3, \(\mu\) cap of 3.0, Elo-difference clip) and in Novara’s PSD shrink (keep going until the matrix can be factored). Anywhere an automated job writes a public number from a flaky API, a floor-or-missing policy needs to be explicit.

**Known pitfalls.** This repo’s stadium floor treats failure as 1.0× rather than as missing, which can hold or inflate a city’s rank. That is the opposite of a conservative missing-data rule.

### 10.3 Static input–output economic impact

**What it is.** A five-step visitor-spend model: fans from capacity × occupancy × visitor mix, times a city-adjusted daily spend and hotel premium, times (1 − displacement), times a city multiplier, divided by metro GDP. The algebra is documented in `assumptions.html`; the finished dollars are hard-coded in `GDP_IMPACT`.

**Where else it applies.** Standard tourism / event-impact arithmetic (FIFA, Deloitte, Oxford Economics style). It can be reused for other multi-host events if the workbook that produced the table is kept with the code. It is not used in the odds model or in any retirement engine.

**Known pitfalls.** The formula is not computed in code, hotel room-nights are not in the repo, and the totals do not change as matches are played. A prose line says New York is “0.03%” of GDP; the table and the code say 0.027%. There are no tests.

## 11. Run recipe

Requires Python 3.11+ and network access to Wikimedia. `SETUP_GUIDE.md` describes a from-scratch GitHub Pages copy.

```bash
git clone https://github.com/Tangerineman83/World-Cup-2026-Tracker
cd World-Cup-2026-Tracker
python3 scripts/fetch_trends.py    # writes data/data.json; needs network
# site: python3 -m http.server 8000  and open index.html / assumptions.html
```

- **Entry:** `main()` in `scripts/fetch_trends.py`. The Action is `.github/workflows/fetch-trends.yml`.
- **Inputs to edit:** `CITIES`, `BASELINE_YEARS`, weights and clamps, `GDP_IMPACT`, and `CITY_MATCH_KICKOFFS` in that script; prose assumptions in `assumptions.html`.
- There is no seed.

## 12. Parameters marked not specified in repo

- The workbook / script that produced `GDP_IMPACT` from the named sources, including hotel room-nights and the exact 20% premium algebra.
- The growth rates used to take BEA 2023 MSA GDP to a 2025 estimate.
- A coded justification of the 50/50 pageview weights and of each multiplier / displacement tier beyond the literature citations on the assumptions page.

