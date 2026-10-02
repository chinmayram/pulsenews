---
name: realtime_tester
description: >-
  Autonomous real-time news refresh verification sub-agent skill for PulseNews.
  Use this skill to test, audit, and verify whether news scraping, backend API endpoints (/api/news/refresh),
  and multi-source news feeds (Google, MSN, Yahoo, X, Moneycontrol) are updating in real-time.
---

# Realtime Tester Sub-Agent Skill (`realtime_tester`)

The **Realtime Tester** skill provides an automated audit runbook and executable test suite to verify whether PulseNews is refreshing news feeds in real-time across all 5 news engines.

## Capabilities & Verification Scope

1. **Backend API Real-Time Test**:
   - Sends live `POST /api/news/refresh` requests to the running FastAPI server (`http://localhost:8000`).
   - Verifies response headers (`Cache-Control: no-cache, no-store`).
   - Measures end-to-end API refresh duration (pass threshold: `< 12 seconds`).
   - Validates article counts, dynamic location/topic/source filter breakdowns, and `last_refreshed` timestamp update.

2. **Per-Engine Real-Time Scraper Audit**:
   - Tests individual scrapers concurrently:
     - **Google News** (`scrapers/google_news.py`)
     - **MSN News** (`scrapers/msn_news.py`)
     - **Yahoo News** (`scrapers/yahoo_news.py`)
     - **Verified X (Twitter) News** (`scrapers/x_news.py`)
     - **Moneycontrol Markets** (`scrapers/moneycontrol_news.py`)
   - Measures per-engine execution duration.
   - Calculates freshness metrics:
     - Articles published `< 1 hour`
     - Articles published `< 3 hours`
     - Articles published `< 12 hours`

3. **Static Snapshot Synchronizer**:
   - Verifies `./data/news.json` export and static fallback integrity for GitHub Pages.

---

## Executing the Real-Time Audit

Run the executable real-time test script:

```bash
python .agents/skills/realtime_tester/scripts/test_realtime.py
```

### Expected Output Summary

- **Overall Health Status**: `REALTIME_OK` (Pass) or `DEGRADED` / `FAILED`
- **Per-Source Scrape Speeds**:
  - Google News: ~1.5 - 3s
  - MSN News: ~3 - 5s
  - Yahoo News: ~2 - 4s
  - X (Twitter) News: ~2 - 4s
  - Moneycontrol: ~1 - 3s
- **Full 5-Engine Aggregator Latency**: `< 8 seconds`
- **Freshness**: Top breaking headlines published within the last 5 to 180 minutes.
