"""
PulseNews Static Exporter for GitHub Pages
Runs news scrapers in parallel and exports static JSON files to data/news.json
"""
import asyncio
import json
from pathlib import Path
from scrapers.aggregator import aggregator
from config import LOCATIONS, TOPICS, SOURCES

async def main():
    print("=== PulseNews Static Exporter ===")
    print("Scraping all 5 news sources (Google, MSN, Yahoo, X, Moneycontrol)...")
    
    await aggregator.refresh_all(force=True)
    all_articles = aggregator.get_articles(location="all", topic="all", source="all")
    filter_counts = aggregator.get_filter_counts()

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    news_data = {
        "status": "success",
        "count": len(all_articles),
        "last_refreshed": aggregator.last_refreshed,
        "filter_counts": filter_counts,
        "articles": [a.model_dump() for a in all_articles]
    }

    with open(data_dir / "news.json", "w", encoding="utf-8") as f:
        json.dump(news_data, f, indent=2)

    config_data = {
        "locations": LOCATIONS,
        "topics": TOPICS,
        "sources": SOURCES,
        "priority_order": ["job_market", "technology", "entertainment", "general"],
        "enabled_topics": {t: True for t in ["job_market", "technology", "entertainment", "general"]}
    }

    with open(data_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    print(f"Export completed! {len(all_articles)} articles saved to data/news.json")

if __name__ == "__main__":
    asyncio.run(main())
