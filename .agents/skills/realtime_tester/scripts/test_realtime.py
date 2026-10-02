#!/usr/bin/env python3
"""
Realtime Tester Sub-Agent Executable Script
Audits and benchmarks real-time news refresh across FastAPI endpoints & 5 scraper engines.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
import httpx

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
os.chdir(str(WORKSPACE_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from scrapers.google_news import scrape_google_news
from scrapers.msn_news import scrape_msn_news
from scrapers.yahoo_news import scrape_yahoo_news
from scrapers.x_news import scrape_x_news
from scrapers.moneycontrol_news import scrape_moneycontrol_news
from scrapers.aggregator import aggregator

async def audit_direct_scrapers():
    print("=" * 70)
    print(" 1. INDIVIDUAL SCRAPER ENGINE REAL-TIME BENCHMARKS")
    print("=" * 70)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    results = {}
    scrapers = [
        ("Google News", scrape_google_news),
        ("MSN News", scrape_msn_news),
        ("Yahoo News", scrape_yahoo_news),
        ("X (Twitter)", scrape_x_news),
        ("Moneycontrol", scrape_moneycontrol_news),
    ]

    async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
        for name, fn in scrapers:
            t0 = time.time()
            try:
                arts = await fn(client)
                dur = time.time() - t0
                now = time.time()
                u1h = len([a for a in arts if (now - a.timestamp) <= 3600])
                u3h = len([a for a in arts if (now - a.timestamp) <= 10800])
                newest_age_min = ((now - arts[0].timestamp) / 60) if arts else 999.0

                results[name] = {
                    "count": len(arts),
                    "duration": dur,
                    "under_1h": u1h,
                    "under_3h": u3h,
                    "newest_age_min": newest_age_min,
                    "status": "REALTIME_OK" if dur <= 10.0 and len(arts) > 0 else "SLOW"
                }

                print(f" ► {name:15s} | Time: {dur:5.2f}s | Articles: {len(arts):4d} | Newest: {newest_age_min:5.1f}m ago | <1h: {u1h:2d} | <3h: {u3h:2d} | Status: [{results[name]['status']}]")
            except Exception as e:
                dur = time.time() - t0
                results[name] = {"count": 0, "duration": dur, "error": str(e), "status": "ERROR"}
                print(f" ► {name:15s} | Time: {dur:5.2f}s | FAILED: {e}")

    return results

async def audit_full_aggregator():
    print("\n" + "=" * 70)
    print(" 2. FULL MULTI-SOURCE AGGREGATOR REFRESH AUDIT")
    print("=" * 70)

    t0 = time.time()
    articles = await aggregator.refresh_all(force=True)
    dur = time.time() - t0
    counts = aggregator.get_filter_counts()

    print(f"Aggregator Refresh Completed in: {dur:.2f} seconds!")
    print(f"Total Aggregated Articles (24h cutoff): {len(articles)}")
    print(f"Source Distribution: {counts['sources']}")
    print(f"Topic Distribution:  {counts['topics']}")
    print(f"Location Distribution: {counts['locations']}")

    return {"duration": dur, "count": len(articles), "counts": counts}

async def audit_api_endpoint():
    print("\n" + "=" * 70)
    print(" 3. FASTAPI BACKEND API LIVE REFRESH ENDPOINT TEST")
    print("=" * 70)

    url = "http://localhost:8000/api/news/refresh?location=all&topic=priority&source=all&limit=150"
    t0 = time.time()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url)
            dur = time.time() - t0
            if resp.status_code == 200:
                data = resp.json()
                print(f"API Endpoint Status: HTTP 200 OK")
                print(f"API Response Latency: {dur:.2f} seconds")
                print(f"Cache Control Header: {resp.headers.get('Cache-Control')}")
                print(f"Response Article Count: {data.get('count')}")
                print(f"Total Dataset Count:   {data.get('total_available')}")
                print(f"Last Refreshed Epoch:  {data.get('last_refreshed')}")
                print(f"Result Message:        {data.get('message')}")
                return {"status": "PASS", "duration": dur, "count": data.get("count")}
            else:
                print(f"API Endpoint Error: HTTP {resp.status_code}")
                return {"status": "FAIL", "duration": dur, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        print(f"API Request Error (Server might be offline): {e}")
        return {"status": "FAIL", "error": str(e)}

async def main():
    print("⚡ PULSENEWS REALTIME_TESTER SUB-AGENT AUDIT RUN ⚡\n")
    direct_res = await audit_direct_scrapers()
    agg_res = await audit_full_aggregator()
    api_res = await audit_api_endpoint()

    print("\n" + "=" * 70)
    print(" FINAL REAL-TIME VERIFICATION SUMMARY")
    print("=" * 70)

    all_fast = all(v.get("duration", 99) < 10 for v in direct_res.values())
    agg_fast = agg_res["duration"] < 12.0
    api_pass = api_res.get("status") == "PASS"

    if all_fast and agg_fast and api_pass:
        overall = "✅ REALTIME_OK (ALL TESTS PASSED)"
    elif agg_fast:
        overall = "⚠️ REALTIME_DEGRADED (API or Scraper warning)"
    else:
        overall = "❌ REALTIME_FAILED"

    print(f"Overall Status: {overall}")
    print(f"Scrapers Average Latency: {sum(v.get('duration', 0) for v in direct_res.values()) / max(1, len(direct_res)):.2f}s")
    print(f"Full Scrape Duration:    {agg_res['duration']:.2f}s")
    print(f"API Endpoint Latency:   {api_res.get('duration', 0):.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
