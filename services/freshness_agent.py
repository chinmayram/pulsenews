"""
PulseNews Real-Time Freshness & Recency Audit Sub-Agent
Autonomous QA sub-agent to audit whether news sources are actively fetching the latest news.

Features:
1. Real-time recency tracking per source engine (minutes since newest publication).
2. Multi-tier freshness distribution (<30m, <1h, <3h, <6h, <24h, >24h).
3. SLA-based health grading (REALTIME_OK, LAGGING, STALE, OFFLINE).
4. Live upstream query probing to differentiate feed latency vs publisher lull.
5. Autonomous auto-fix / re-scrape remediation for lagging sources.
6. Machine-readable reporting (data/freshness_report.json) & formatted terminal display.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from dateutil import parser as date_parser

from config import SOURCES
from scrapers.aggregator import aggregator

class NewsFreshnessSubAgent:
    """Sub-agent dedicated to checking news freshness and recency across all sources."""

    # Maximum acceptable age (in minutes) for the newest article before flagging
    ENGINE_SLAS_MINUTES = {
        "google": 30.0,        # Google News RSS updates continuously (sub-30m)
        "x": 30.0,             # X (Twitter) breaking feeds (sub-30m)
        "moneycontrol": 45.0,  # Moneycontrol market updates (sub-45m)
        "yahoo": 60.0,         # Yahoo News RSS (sub-60m)
        "msn": 480.0           # MSN / Bing News RSS batch pipeline (~6-8h)
    }

    PROBE_QUERIES = {
        "google": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "x": "https://news.google.com/rss/search?q=(site:x.com+OR+site:twitter.com)+India+when:1h&hl=en-IN&gl=IN&ceid=IN:en",
        "yahoo": "https://news.yahoo.com/rss/",
        "moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
        "msn": "https://www.bing.com/news/search?q=India&qft=sortbydate%3d%221%22&format=rss"
    }

    def __init__(self):
        self.report: Dict[str, Any] = {}

    async def probe_live_feed(self, source: str, url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Probes a live feed directly to measure network latency and live feed recency."""
        t0 = time.time()
        import feedparser
        try:
            resp = await client.get(url, timeout=12.0, follow_redirects=True)
            latency_ms = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                entries = feed.entries
                newest_ts = None
                newest_pub = None
                newest_title = None

                for e in entries:
                    pub = e.get("published", "")
                    if pub:
                        try:
                            dt = date_parser.parse(pub)
                            ts = dt.timestamp()
                            if newest_ts is None or ts > newest_ts:
                                newest_ts = ts
                                newest_pub = pub
                                newest_title = e.get("title", "")
                        except Exception:
                            pass

                now = time.time()
                age_min = round((now - newest_ts) / 60, 1) if newest_ts else None

                return {
                    "status": "ONLINE",
                    "http_status": 200,
                    "latency_ms": latency_ms,
                    "entry_count": len(entries),
                    "live_newest_age_min": age_min,
                    "live_newest_published": newest_pub,
                    "live_newest_title": newest_title[:80] if newest_title else None
                }
            else:
                return {
                    "status": "ERROR",
                    "http_status": resp.status_code,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}"
                }
        except Exception as ex:
            return {
                "status": "FAILED",
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(ex)
            }

    async def check_all_sources(
        self,
        news_file_path: str = "data/news.json",
        probe_live: bool = True,
        auto_fix: bool = False
    ) -> Dict[str, Any]:
        """Audits the freshness of all sources and optionally runs auto-fix."""
        t_start = time.time()
        now = time.time()

        news_path = Path(news_file_path)
        if not news_path.exists():
            print(f"[Freshness Sub-Agent] {news_file_path} not found. Running initial scrape...")
            await aggregator.refresh_all(force=True)
            self._save_dataset(news_file_path)

        with open(news_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        articles = dataset.get("articles", [])
        last_refreshed_iso = dataset.get("last_refreshed", "")

        # Probe live feeds concurrently
        live_probes = {}
        if probe_live:
            async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
                tasks = {
                    src: self.probe_live_feed(src, url, client)
                    for src, url in self.PROBE_QUERIES.items()
                }
                probe_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for src, res in zip(tasks.keys(), probe_results):
                    if isinstance(res, dict):
                        live_probes[src] = res
                    else:
                        live_probes[src] = {"status": "FAILED", "error": str(res)}

        # Analyze current article pool per source
        sources_analyzed = {}
        active_sources = [s for s in SOURCES if s != "all"]
        system_issues = []

        for src in active_sources:
            src_articles = [a for a in articles if a.get("source") == src]
            sla = self.ENGINE_SLAS_MINUTES.get(src, 60.0)

            if not src_articles:
                status = "OFFLINE"
                system_issues.append(f"Source '{src}' has 0 articles in dataset!")
                sources_analyzed[src] = {
                    "source": src,
                    "status": status,
                    "article_count": 0,
                    "newest_age_min": None,
                    "oldest_age_h": None,
                    "newest_article": None,
                    "sla_minutes": sla,
                    "buckets": {
                        "under_30m": 0,
                        "30m_to_1h": 0,
                        "1h_to_3h": 0,
                        "3h_to_6h": 0,
                        "6h_to_24h": 0,
                        "over_24h": 0
                    },
                    "live_probe": live_probes.get(src)
                }
                continue

            # Compute min and max ages
            ages_sec = [(now - (a.get("timestamp") or now)) for a in src_articles]
            min_sec = min(ages_sec)
            max_sec = max(ages_sec)
            min_min = round(min_sec / 60, 1)
            max_h = round(max_sec / 3600, 1)

            # Sort source articles by timestamp descending to find newest
            sorted_src = sorted(src_articles, key=lambda x: x.get("timestamp") or 0, reverse=True)
            newest = sorted_src[0]

            # Distribution buckets
            b_30m = sum(1 for s in ages_sec if s <= 30 * 60)
            b_1h = sum(1 for s in ages_sec if 30 * 60 < s <= 60 * 60)
            b_3h = sum(1 for s in ages_sec if 60 * 60 < s <= 3 * 3600)
            b_6h = sum(1 for s in ages_sec if 3 * 3600 < s <= 6 * 3600)
            b_24h = sum(1 for s in ages_sec if 6 * 3600 < s <= 24 * 3600)
            b_over24h = sum(1 for s in ages_sec if s > 24 * 3600)

            # Status classification
            if b_over24h > 0:
                status = "STALE_VIOLATION"
                system_issues.append(f"Source '{src}' contains {b_over24h} articles older than 24 hours.")
            elif min_min <= sla:
                status = "REALTIME_OK"
            elif min_min <= sla * 2.0:
                status = "LAGGING"
                system_issues.append(f"Source '{src}' is lagging: newest article is {min_min}m old (SLA: {sla}m).")
            else:
                status = "STALE"
                system_issues.append(f"Source '{src}' is stale: newest article is {min_min}m old (SLA: {sla}m).")

            sources_analyzed[src] = {
                "source": src,
                "status": status,
                "article_count": len(src_articles),
                "newest_age_min": min_min,
                "oldest_age_h": max_h,
                "sla_minutes": sla,
                "is_fetching_latest": min_min <= (sla * 1.5),
                "newest_article": {
                    "title": newest.get("title"),
                    "link": newest.get("link"),
                    "published_at": newest.get("published_at"),
                    "published_relative": newest.get("published_relative"),
                    "location": newest.get("location"),
                    "topic": newest.get("topic")
                },
                "buckets": {
                    "under_30m": b_30m,
                    "30m_to_1h": b_1h,
                    "1h_to_3h": b_3h,
                    "3h_to_6h": b_6h,
                    "6h_to_24h": b_24h,
                    "over_24h": b_over24h
                },
                "live_probe": live_probes.get(src)
            }

        # Auto-fix if requested and any source is lagging/stale
        fixes_applied = []
        if auto_fix and system_issues:
            print(f"\n[Freshness Sub-Agent] Auto-Fix triggered for {len(system_issues)} detected issue(s)...")
            await aggregator.refresh_all(force=True)
            self._save_dataset(news_file_path)
            fixes_applied.append("Forced re-scrape of all news sources and regenerated dataset with strict 24h & chronological sorting.")
            # Re-run evaluation without recursive auto_fix
            return await self.check_all_sources(news_file_path=news_file_path, probe_live=False, auto_fix=False)

        duration = round(time.time() - t_start, 2)
        overall_status = "HEALTHY" if not system_issues else ("WARNING" if all(s["article_count"] > 0 for s in sources_analyzed.values()) else "CRITICAL")

        self.report = {
            "timestamp": time.time(),
            "last_refreshed_iso": last_refreshed_iso,
            "overall_status": overall_status,
            "duration_seconds": duration,
            "total_articles": len(articles),
            "sources": sources_analyzed,
            "issues": system_issues,
            "fixes_applied": fixes_applied
        }

        # Save to report file
        with open("data/freshness_report.json", "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        return self.report

    def _save_dataset(self, target_path: str = "data/news.json"):
        """Saves active aggregator state to JSON."""
        all_articles = aggregator.get_articles(location="all", topic="all", source="all")
        filter_counts = aggregator.get_filter_counts()
        news_data = {
            "status": "success",
            "count": len(all_articles),
            "last_refreshed": aggregator.last_refreshed,
            "filter_counts": filter_counts,
            "articles": [a.model_dump() for a in all_articles]
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(news_data, f, indent=2)

    def print_terminal_report(self, report: Optional[Dict[str, Any]] = None):
        """Displays formatted report in console."""
        rep = report or self.report
        if not rep:
            print("No report data available.")
            return

        print("\n" + "=" * 80)
        print(f"  PULSENEWS FRESHNESS SUB-AGENT REPORT  [{rep.get('overall_status')}]")
        print(f"  Audit Duration: {rep.get('duration_seconds')}s | Total Articles: {rep.get('total_articles')}")
        print("=" * 80)

        # Header
        header = f"{'Source':13} | {'Status':13} | {'Newest Age':11} | {'Count':6} | {'<30m':5} | {'<1h':5} | {'<3h':5} | {'<24h':6} | {'Live Probe':12}"
        print(header)
        print("-" * len(header))

        for src, data in rep.get("sources", {}).items():
            status = data.get("status", "UNKNOWN")
            count = data.get("article_count", 0)
            newest_age = f"{data.get('newest_age_min')}m" if data.get('newest_age_min') is not None else "N/A"
            b = data.get("buckets", {})
            b_30m = b.get("under_30m", 0)
            b_1h = b.get("30m_to_1h", 0)
            b_3h = b.get("1h_to_3h", 0)
            b_24h = b.get("6h_to_24h", 0) + b.get("3h_to_6h", 0) + b_3h + b_1h + b_30m

            probe = data.get("live_probe") or {}
            probe_str = f"{probe.get('latency_ms', '?')}ms" if probe.get("status") == "ONLINE" else probe.get("status", "N/A")

            row = f"{src.upper():13} | {status:13} | {newest_age:11} | {count:6} | {b_30m:5} | {b_1h:5} | {b_3h:5} | {b_24h:6} | {probe_str:12}"
            print(row)

        print("-" * len(header))

        # Detail on newest stories per engine
        print("\n=== LATEST ARTICLE PREVIEW PER SOURCE ===")
        for src, data in rep.get("sources", {}).items():
            newest = data.get("newest_article")
            if newest:
                rel = newest.get("published_relative", "")
                title = newest.get("title", "")
                # Clean up title for console encoding
                clean_title = title.encode("ascii", "ignore").decode()
                print(f"[{src.upper()}] ({rel}): {clean_title[:75]}")
            else:
                print(f"[{src.upper()}]: No articles found!")

        # Issues
        issues = rep.get("issues", [])
        if issues:
            print("\n[!] DETECTED ISSUES / BOTTLENECKS:")
            for iss in issues:
                print(f"  - {iss}")
        else:
            print("\n[OK] All news sources are actively fetching latest news within SLA!")

        print("=" * 80 + "\n")

freshness_agent = NewsFreshnessSubAgent()

if __name__ == "__main__":
    import sys
    auto_fix_flag = "--auto-fix" in sys.argv
    asyncio.run(freshness_agent.check_all_sources(auto_fix=auto_fix_flag))
    freshness_agent.print_terminal_report()
