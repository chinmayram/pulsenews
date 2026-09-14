import asyncio
import json
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Set
import httpx

from scrapers.models import NewsArticle, is_valid_headline
from scrapers.google_news import scrape_google_news
from scrapers.msn_news import scrape_msn_news
from scrapers.yahoo_news import scrape_yahoo_news
from scrapers.x_news import scrape_x_news
from scrapers.moneycontrol_news import scrape_moneycontrol_news
from config import LOCATIONS, TOPICS, SOURCES, load_settings

class NewsAggregator:
    def __init__(self):
        self.articles: List[NewsArticle] = []
        self.last_refreshed: float = 0
        self.is_refreshing: bool = False
        self._lock = asyncio.Lock()

    def normalize_title(self, title: str) -> str:
        cleaned = re.sub(r"[^\w\s]", "", title.lower())
        return " ".join(cleaned.split()[:7])

    def deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        seen_ids: Set[str] = set()
        seen_titles: Set[str] = set()
        unique: List[NewsArticle] = []

        for art in articles:
            if art.id in seen_ids:
                continue
            norm_title = self.normalize_title(art.title)
            if norm_title in seen_titles and len(norm_title) > 10:
                continue

            seen_ids.add(art.id)
            seen_titles.add(norm_title)
            unique.append(art)

        return unique

    async def refresh_all(self, force: bool = False) -> List[NewsArticle]:
        now = time.time()
        if not force and (now - self.last_refreshed) < 30 and self.articles:
            return self.articles

        async with self._lock:
            self.is_refreshing = True
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                }
                limits = httpx.Limits(max_connections=60, max_keepalive_connections=25)
                async with httpx.AsyncClient(headers=headers, limits=limits, timeout=15.0, follow_redirects=True) as client:
                    tasks = [
                        scrape_google_news(client),
                        scrape_msn_news(client),
                        scrape_yahoo_news(client),
                        scrape_x_news(client),
                        scrape_moneycontrol_news(client),
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    combined: List[NewsArticle] = []
                    for res in results:
                        if isinstance(res, list):
                            combined.extend(res)
                        elif isinstance(res, Exception):
                            print(f"[Aggregator] Scraper error: {res}")

                    # 24-hour cutoff: Keep strictly news from the last 24 hours with valid editorial headlines
                    now = time.time()
                    combined = [
                        a for a in combined 
                        if (now - a.timestamp) <= (24 * 3600) and is_valid_headline(a.title, a.summary, a.link)
                    ]

                    # Sort newest first & deduplicate
                    combined.sort(key=lambda a: a.timestamp, reverse=True)
                    self.articles = self.deduplicate(combined)
                    self.last_refreshed = time.time()
                    self.save_to_json()
            finally:
                self.is_refreshing = False

        return self.articles

    def save_to_json(self, file_path: Optional[Path] = None) -> bool:
        if file_path is None:
            file_path = Path(__file__).resolve().parent.parent / "data" / "news.json"
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            all_articles = self.get_articles(location="all", topic="all", source="all")
            filter_counts = self.get_filter_counts()
            news_data = {
                "status": "success",
                "count": len(all_articles),
                "last_refreshed": self.last_refreshed,
                "filter_counts": filter_counts,
                "articles": [a.model_dump() for a in all_articles]
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(news_data, f, indent=2)
            return True
        except Exception as e:
            print(f"[Aggregator] Error saving news to {file_path}: {e}")
            return False

    def get_articles(
        self,
        location: Optional[str] = "all",
        topic: Optional[str] = "priority",
        source: Optional[str] = "all",
        search_query: Optional[str] = None
    ) -> List[NewsArticle]:
        settings = load_settings()
        priority_order = settings.get("priority_order", ["job_market", "technology", "entertainment", "general"])
        enabled_topics = settings.get("enabled_topics", {})

        now = time.time()
        filtered = [a for a in self.articles if (now - a.timestamp) <= (24 * 3600)]

        # 1. Location filter
        if location and location != "all":
            filtered = [a for a in filtered if a.location.lower() == location.lower()]

        # 2. Source filter
        if source and source != "all":
            filtered = [a for a in filtered if a.source.lower() == source.lower()]

        # 3. Search query filter
        if search_query and search_query.strip():
            q = search_query.strip().lower()
            filtered = [
                a for a in filtered
                if q in a.title.lower() or q in a.summary.lower() or q in a.source_name.lower() or q in a.location_name.lower() or q in a.topic_name.lower()
            ]

        # 4. Topic filter
        if topic and topic != "all" and topic != "priority":
            filtered = [a for a in filtered if a.topic.lower() == topic.lower()]
        elif topic == "priority":
            # "priority" view: filter to enabled topics
            active_topics = set(t for t in priority_order if t in TOPICS and t != "priority" and enabled_topics.get(t, True))
            for dt in ["job_market", "technology", "entertainment", "general"]:
                if enabled_topics.get(dt, True):
                    active_topics.add(dt)
            filtered = [a for a in filtered if a.topic.lower() in active_topics]

        # Deduplicate
        filtered = self.deduplicate(filtered)

        # STRICT REQUIREMENT: Always sort from newest to oldest (latest news 1st then old)
        filtered.sort(key=lambda a: a.timestamp, reverse=True)

        return filtered

    def get_filter_counts(
        self,
        active_location: Optional[str] = "all",
        active_topic: Optional[str] = "priority",
        active_source: Optional[str] = "all",
        search_query: Optional[str] = None
    ) -> Dict:
        """Calculates interactive cross-counts for Location, Topic, and Source chips within 24 hours."""
        now = time.time()
        base = [a for a in self.articles if (now - a.timestamp) <= (24 * 3600)]
        if search_query and search_query.strip():
            q = search_query.strip().lower()
            base = [
                a for a in base
                if q in a.title.lower() or q in a.summary.lower() or q in a.source_name.lower()
            ]

        # 1. Location Counts (conditioned on active topic and active source)
        loc_base = base
        if active_source and active_source != "all":
            loc_base = [a for a in loc_base if a.source.lower() == active_source.lower()]
        if active_topic and active_topic != "all" and active_topic != "priority":
            loc_base = [a for a in loc_base if a.topic.lower() == active_topic.lower()]

        location_counts = {"all": len(loc_base)}
        for loc_id in LOCATIONS.keys():
            if loc_id != "all":
                location_counts[loc_id] = sum(1 for a in loc_base if a.location.lower() == loc_id)

        # 2. Topic Counts (conditioned on active location and active source)
        top_base = base
        if active_location and active_location != "all":
            top_base = [a for a in top_base if a.location.lower() == active_location.lower()]
        if active_source and active_source != "all":
            top_base = [a for a in top_base if a.source.lower() == active_source.lower()]

        topic_counts = {"all": len(top_base), "priority": len(top_base)}
        for top_id in TOPICS.keys():
            if top_id not in ("all", "priority"):
                topic_counts[top_id] = sum(1 for a in top_base if a.topic.lower() == top_id)

        # 3. Source Counts (conditioned on active location and active topic)
        src_base = base
        if active_location and active_location != "all":
            src_base = [a for a in src_base if a.location.lower() == active_location.lower()]
        if active_topic and active_topic != "all" and active_topic != "priority":
            src_base = [a for a in src_base if a.topic.lower() == active_topic.lower()]

        source_counts = {s: 0 for s in SOURCES.keys()}
        source_counts["all"] = len(src_base)
        for a in src_base:
            if a.source.lower() in source_counts:
                source_counts[a.source.lower()] += 1

        return {
            "locations": location_counts,
            "topics": topic_counts,
            "sources": source_counts,
            "total_articles": len(self.articles),
            "last_refreshed": self.last_refreshed,
            "is_refreshing": self.is_refreshing
        }

aggregator = NewsAggregator()
