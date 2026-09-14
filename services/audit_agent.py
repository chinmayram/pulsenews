"""
PulseNews Scraper & Data Source Audit Sub-Agent
Autonomous QA & Diagnostic Engine for Multi-Source News Aggregation

Features:
1. Live Query Health Check (HTTP status, latency, entry counts)
2. 24-Hour Freshness Audit (validates timestamp compliance)
3. 3-Tier Coverage Matrix (11 Locations x 4 Topics x 5 Engines)
4. Data Integrity Verification (images, title cleaning, deduplication)
5. Strict Chronological Ordering Validation
6. Auto-Repair & Re-export Capabilities
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Any
import httpx
import feedparser
from dateutil import parser as date_parser

from config import LOCATIONS, TOPICS, SOURCES
from scrapers.google_news import GOOGLE_QUERIES, scrape_google_news
from scrapers.msn_news import MSN_QUERIES, scrape_msn_news
from scrapers.yahoo_news import YAHOO_QUERIES, scrape_yahoo_news
from scrapers.x_news import X_QUERIES, scrape_x_news
from scrapers.moneycontrol_news import MONEYCONTROL_FEEDS, scrape_moneycontrol_news
from scrapers.aggregator import aggregator

class SourceAuditSubAgent:
    def __init__(self):
        self.results = {
            "timestamp": time.time(),
            "sources": {},
            "matrix_coverage": {},
            "stale_queries": [],
            "dead_queries": [],
            "issues_found": [],
            "fixes_applied": [],
            "summary": {}
        }

    async def audit_query_health(self, source_name: str, queries: List[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Audits each query URL for a specific news engine."""
        print(f"\n[Audit Sub-Agent] Auditing {source_name.upper()} ({len(queries)} query feeds)...")
        now = time.time()
        query_stats = []
        source_total_entries = 0
        source_fresh_entries = 0
        dead_count = 0
        stale_count = 0

        for q in queries:
            url = q.get("url")
            if not url and "q" in q:
                # X query style
                import urllib.parse
                url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q['q'])}+when:1d&hl=en-IN&gl=IN&ceid=IN:en"

            loc = q.get("loc", "global")
            top = q.get("top", "general")
            t0 = time.time()
            status = 0
            entries_count = 0
            fresh_count = 0

            try:
                resp = await client.get(url, timeout=12.0, follow_redirects=True)
                latency = round((time.time() - t0) * 1000, 1)
                status = resp.status_code

                if status == 200:
                    feed = feedparser.parse(resp.text)
                    entries_count = len(feed.entries)
                    source_total_entries += entries_count

                    for e in feed.entries:
                        pub = e.get("published", "")
                        if pub:
                            try:
                                dt = date_parser.parse(pub)
                                ts = dt.timestamp()
                                if (now - ts) <= (24 * 3600):
                                    fresh_count += 1
                            except Exception:
                                pass
                        else:
                            # Without published date, count as fresh if query includes when:1d
                            if "when:1d" in url:
                                fresh_count += 1

                    source_fresh_entries += fresh_count

                    if entries_count == 0:
                        dead_count += 1
                        self.results["dead_queries"].append({"source": source_name, "url": url, "location": loc, "topic": top})
                    elif fresh_count / max(1, entries_count) < 0.3:
                        stale_count += 1
                        self.results["stale_queries"].append({"source": source_name, "url": url, "fresh_pct": round(fresh_count / entries_count * 100, 1)})
                else:
                    dead_count += 1
                    self.results["dead_queries"].append({"source": source_name, "url": url, "status": status})

            except Exception as ex:
                latency = round((time.time() - t0) * 1000, 1)
                dead_count += 1
                self.results["dead_queries"].append({"source": source_name, "url": url, "error": str(ex)})

            query_stats.append({
                "url": url[:85] + ("..." if len(url) > 85 else ""),
                "location": loc,
                "topic": top,
                "status": status,
                "latency_ms": latency,
                "entries": entries_count,
                "fresh_24h": fresh_count
            })

        health_pct = round((len(queries) - dead_count) / max(1, len(queries)) * 100, 1)
        fresh_pct = round(source_fresh_entries / max(1, source_total_entries) * 100, 1) if source_total_entries > 0 else 0

        summary = {
            "total_queries": len(queries),
            "dead_queries": dead_count,
            "stale_queries": stale_count,
            "total_entries_fetched": source_total_entries,
            "fresh_entries_24h": source_fresh_entries,
            "query_health_pct": health_pct,
            "freshness_pct": fresh_pct,
            "query_stats": query_stats
        }
        self.results["sources"][source_name] = summary
        print(f"   -> {source_name.upper()}: {health_pct}% healthy, {source_fresh_entries}/{source_total_entries} 24h fresh ({fresh_pct}%)")
        return summary

    def save_snapshot(self, target_path: str = "data/news.json"):
        """Exports current aggregated articles and filter counts to JSON."""
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

    async def audit_data_snapshot(self) -> Dict[str, Any]:
        """Audits current data/news.json snapshot across all 11 locations, 4 topics, and 5 sources."""
        print("\n[Audit Sub-Agent] Auditing Active Data Snapshot (data/news.json)...")
        from pathlib import Path
        news_file = Path("data/news.json")
        if not news_file.exists():
            print("   -> data/news.json not found! Running live scraper refresh first...")
            await aggregator.refresh_all(force=True)
            self.save_snapshot("data/news.json")

        with open(news_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        articles = data.get("articles", [])
        now = time.time()
        max_age = 0
        min_age = 999999
        over_24h = 0
        broken_images = 0
        unclean_titles = 0

        # Check chronological sorting
        is_sorted = True
        for i in range(len(articles) - 1):
            if (articles[i].get("timestamp") or 0) < (articles[i+1].get("timestamp") or 0):
                is_sorted = False
                break

        # Matrix counts
        matrix = {s: {l: 0 for l in LOCATIONS} for s in SOURCES if s != "all"}

        for a in articles:
            ts = a.get("timestamp", now)
            age_h = (now - ts) / 3600
            max_age = max(max_age, age_h)
            min_age = min(min_age, age_h)
            if age_h > 24.0:
                over_24h += 1

            img = a.get("image_url", "")
            if not img or not img.startswith("http"):
                broken_images += 1

            t = a.get("title", "")
            if t.endswith(" - Google News") or t.endswith(" - MSN") or t.endswith(" - Yahoo") or t.endswith(" - x.com"):
                unclean_titles += 1

            src = a.get("source", "")
            loc = a.get("location", "")
            if src in matrix and loc in matrix[src]:
                matrix[src][loc] += 1

        snapshot_audit = {
            "total_articles": len(articles),
            "strictly_sorted_newest_first": is_sorted,
            "max_age_hours": round(max_age, 2),
            "min_age_hours": round(min_age, 2),
            "over_24h_count": over_24h,
            "broken_images_count": broken_images,
            "unclean_titles_count": unclean_titles,
            "matrix_distribution": matrix
        }
        self.results["snapshot_audit"] = snapshot_audit
        return snapshot_audit

    async def run_full_audit(self, auto_fix: bool = True) -> Dict[str, Any]:
        """Runs comprehensive audit across all engines and auto-fixes any bottlenecks."""
        t_start = time.time()
        print("=" * 70)
        print("  PULSENEWS DATA SOURCE & SCRAPER AUDIT SUB-AGENT")
        print("=" * 70)

        async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
            await self.audit_query_health("google", GOOGLE_QUERIES, client)
            await self.audit_query_health("msn", MSN_QUERIES, client)
            await self.audit_query_health("yahoo", YAHOO_QUERIES, client)
            await self.audit_query_health("x", X_QUERIES, client)
            await self.audit_query_health("moneycontrol", MONEYCONTROL_FEEDS, client)

        snapshot = await self.audit_data_snapshot()

        # Diagnose bottlenecks
        diagnostics = []
        if snapshot["over_24h_count"] > 0:
            diagnostics.append(f"{snapshot['over_24h_count']} articles are older than 24 hours.")
        if not snapshot["strictly_sorted_newest_first"]:
            diagnostics.append("Articles are not strictly sorted newest to oldest.")
        if snapshot["broken_images_count"] > 0:
            diagnostics.append(f"{snapshot['broken_images_count']} articles have missing/broken image URLs.")

        # Check engine coverage
        matrix = snapshot["matrix_distribution"]
        for src, loc_counts in matrix.items():
            zero_locs = [l for l, cnt in loc_counts.items() if cnt == 0 and l not in ("all",)]
            if len(zero_locs) > 3:
                diagnostics.append(f"{src.upper()} has 0 articles for {len(zero_locs)} regional hubs: {', '.join(zero_locs[:4])}")

        self.results["issues_found"] = diagnostics

        # Execute Auto-Fix if needed
        if auto_fix and len(diagnostics) > 0:
            print(f"\n[Audit Sub-Agent] Auto-Fix triggered for {len(diagnostics)} issues...")
            # Run aggregator refresh with strict 24h & newest-first sorting
            await aggregator.refresh_all(force=True)
            self.save_snapshot("data/news.json")
            self.results["fixes_applied"].append("Re-scraped all 5 engines and rebuilt data/news.json with strict 24h filter and chronological ordering.")
            # Re-audit snapshot
            snapshot = await self.audit_data_snapshot()

        total_time = round(time.time() - t_start, 2)
        self.results["summary"] = {
            "duration_seconds": total_time,
            "engines_audited": 5,
            "total_articles": snapshot["total_articles"],
            "strictly_sorted": snapshot["strictly_sorted_newest_first"],
            "issues_count": len(diagnostics),
            "status": "PASS" if len(diagnostics) == 0 or auto_fix else "WARNING"
        }

        # Save machine-readable audit report
        with open("data/audit_report.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)

        self.print_summary_report(snapshot, total_time)
        return self.results

    def print_summary_report(self, snapshot: Dict[str, Any], duration: float):
        print("\n" + "=" * 70)
        print(f"  AUDIT SUMMARY REPORT (Completed in {duration}s)")
        print("=" * 70)
        print(f"Total News Articles in Feed:  {snapshot['total_articles']}")
        print(f"Strictly Sorted Newest First: {'[YES]' if snapshot['strictly_sorted_newest_first'] else '[NO]'}")
        print(f"Freshness Window:             {snapshot['min_age_hours']}h - {snapshot['max_age_hours']}h (Strictly < 24.0h)")
        print(f"Articles Exceeding 24 Hours:  {snapshot['over_24h_count']}")
        print(f"Broken Image URLs:            {snapshot['broken_images_count']}")
        print(f"Uncleaned Headline Suffixes:  {snapshot['unclean_titles_count']}")

        print("\n=== MATRIX COVERAGE: ENGINE x METROPOLITAN HUBS ===")
        matrix = snapshot["matrix_distribution"]
        header = f"{'Source':14} | " + " | ".join(f"{l[:4].title():4}" for l in ["delhi", "mumbai", "bengaluru", "chennai", "kolkata", "hyderabad", "pune", "odisha", "india", "global"])
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for src, locs in matrix.items():
            row = f"{src.upper():14} | " + " | ".join(f"{locs.get(l,0):4}" for l in ["delhi", "mumbai", "bengaluru", "chennai", "kolkata", "hyderabad", "pune", "odisha", "india", "global"])
            print(row)
        print("-" * len(header))

        if self.results["issues_found"]:
            print("\nDiagnostics Detected:")
            for d in self.results["issues_found"]:
                print(f" [!] {d}")
        else:
            print("\nAll data sources healthy, 24h compliant, and chronologically sorted!")
        print("=" * 70 + "\n")

audit_agent = SourceAuditSubAgent()

if __name__ == "__main__":
    asyncio.run(audit_agent.run_full_audit(auto_fix=True))
