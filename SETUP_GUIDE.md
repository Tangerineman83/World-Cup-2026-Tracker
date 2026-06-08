# FIFA World Cup 2026 — Interest Tracker
## Complete Setup Guide for GitHub Pages

----

## What you're building

A live website that:
- Shows a league table of Google Trends interest for all 16 host cities
- Updates automatically every Saturday via a scheduled GitHub Action
- Costs nothing to run (GitHub Pages + Actions are free)

---

## File structure

After setup your repo will look like this:

```
wc2026-tracker/
├── index.html                        ← the website
├── data/
│   └── data.json                     ← scores (auto-updated by the Action)
├── scripts/
│   └── fetch_trends.py               ← Python script that fetches Google Trends
└── .github/
    └── workflows/
        └── fetch-trends.yml          ← the schedule that runs fetch_trends.py
```

---

## Step 1 — Create a GitHub account (skip if you have one)

1. Go to **https://github.com** and click **Sign up**
2. Choose a username, enter your email, create a password
3. Verify your email address

---

## Step 2 — Create a new repository

1. Once logged in, click the **+** icon (top-right) → **New repository**
2. Fill in:
   - **Repository name:** `wc2026-tracker` (or anything you like)
   - **Description:** World Cup 2026 host city interest tracker
   - **Public** ← must be Public for free GitHub Pages
   - ✅ **Add a README file** (tick this)
3. Click **Create repository**

---

## Step 3 — Upload the files

You'll upload 4 files. GitHub lets you do this entirely in the browser.

### Upload `index.html` (into the root)

1. In your new repo, click **Add file → Upload files**
2. Drag `index.html` onto the page (or click "choose your files")
3. Scroll down, click **Commit changes**

### Upload `data/data.json`

1. Click **Add file → Create new file**
2. In the filename box type: `data/data.json`
   *(typing the slash automatically creates the `data/` folder)*
3. Open the `data/data.json` file from this package in a text editor,
   select all the text (Ctrl+A / Cmd+A), paste it into the GitHub editor
4. Click **Commit new file**

### Upload `scripts/fetch_trends.py`

1. Click **Add file → Create new file**
2. Filename: `scripts/fetch_trends.py`
3. Paste in the contents of `scripts/fetch_trends.py`
4. Click **Commit new file**

### Upload `.github/workflows/fetch-trends.yml`

1. Click **Add file → Create new file**
2. Filename: `.github/workflows/fetch-trends.yml`
   *(yes, it starts with a dot — type it exactly)*
3. Paste in the contents of `.github/workflows/fetch-trends.yml`
4. Click **Commit new file**

---

## Step 4 — Enable GitHub Pages

1. In your repo, click the **Settings** tab (top menu)
2. In the left sidebar, click **Pages**
3. Under **Source**, select **Deploy from a branch**
4. Under **Branch**, choose **main** and folder **/ (root)**
5. Click **Save**
6. Wait ~60 seconds, then refresh — you'll see a green banner:
   **"Your site is live at https://YOUR-USERNAME.github.io/wc2026-tracker/"**

That URL is your live website. Share it with anyone.

---

## Step 5 — Test the GitHub Action manually

Before waiting for Saturday, run the data fetcher right now to check it works:

1. In your repo, click the **Actions** tab
2. In the left sidebar, click **Fetch Google Trends Data**
3. Click the **Run workflow** button (right side) → **Run workflow**
4. A yellow dot appears — click on it to watch the logs in real time
5. If it turns green ✅, check `data/data.json` — it will now have real scores
6. If it turns red ❌, see the Troubleshooting section below

---

## Step 6 — Verify the live site shows real data

1. Go to your GitHub Pages URL
2. You should see the league table with scores from the Action run
3. The "seed data" warning at the bottom will disappear once real data is in

---

## How the automatic weekly update works

The file `.github/workflows/fetch-trends.yml` contains this line:

```yaml
- cron: "0 8 * * 6"
```

This means: **run at 08:00 UTC every Saturday (day 6 of the week)**.

Every Saturday, GitHub will:
1. Run `fetch_trends.py` (which queries Google Trends for all 16 cities)
2. Write new scores into `data/data.json`
3. Commit and push that file back to your repo
4. Your live site immediately serves the new scores

You don't need to do anything — it's fully automatic.

**To change the schedule**, edit the cron line:
- Every day at midnight: `"0 0 * * *"`
- Every Monday at 9am:   `"0 9 * * 1"`
- Use https://crontab.guru to build custom schedules

---

## Troubleshooting

### ❌ Action fails with "ModuleNotFoundError: No module named 'pytrends'"
This shouldn't happen as the workflow installs pytrends, but if it does:
- Click the failed run → expand the "Install dependencies" step
- Check for error messages and report them

### ❌ Action fails with "429 Too Many Requests" or "ResponseError"
Google Trends rate-limits automated requests. Solutions:
- Wait a few hours and re-run manually (Actions tab → Run workflow)
- The script already includes 3-second delays between batches to be polite
- If it fails regularly, increase `time.sleep(3)` to `time.sleep(8)` in `fetch_trends.py`

### ❌ The website shows "Could not load data.json"
- Make sure `data/data.json` exists in your repo (check the file tree)
- Make sure GitHub Pages is set to serve from the repo root (`/`)
- Clear your browser cache and try again

### ❌ Google Trends returns all zeros
- This can happen if Google detects automation. Wait 24 hours and retry.
- Consider running the Action less frequently (weekly is fine)

### The site shows seed data even after the Action ran successfully
- Hard-reload the page: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- The seed warning disappears once `data.json` no longer contains `"_note"`
  (the fetch script writes a clean file without that field)

---

## Customisation tips

### Change the update schedule
Edit `.github/workflows/fetch-trends.yml`, line:
```yaml
- cron: "0 8 * * 6"
```

### Change the search terms
Edit `scripts/fetch_trends.py`, the `CITIES` list at the top.
The `"term"` field is exactly what gets searched on Google Trends.

### Add the Club World Cup 2025 comparison
Uncomment the CWC cities block in `fetch_trends.py` (or add a second
`CITIES_CWC` list) and write a separate `data/cwc_data.json` file.
Add a toggle button in `index.html` that switches which JSON file is loaded.

---

## Quick-reference checklist

- [ ] GitHub account created
- [ ] New **public** repository created
- [ ] `index.html` uploaded to root
- [ ] `data/data.json` uploaded to `data/` folder
- [ ] `scripts/fetch_trends.py` uploaded to `scripts/` folder
- [ ] `.github/workflows/fetch-trends.yml` uploaded (note the leading dot)
- [ ] GitHub Pages enabled (Settings → Pages → main branch → root)
- [ ] Manual Action run tested and green ✅
- [ ] Live site URL confirmed working

---

*Built with pytrends (unofficial Google Trends API) + GitHub Actions + GitHub Pages.*
*Google Trends data is relative (0–100) and for informational purposes only.*
