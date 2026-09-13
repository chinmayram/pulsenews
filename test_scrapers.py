import asyncio
import time
import httpx
from scrapers.google_news import scrape_google_news
from scrapers.msn_news import scrape_msn_news
from scrapers.yahoo_news import scrape_yahoo_news
from scrapers.x_news import scrape_x_news
from scrapers.aggregator import aggregator

async def run_tests():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
        print("=== Testing Google News Scraper ===")
        g_arts = await scrape_google_news(client)
        print(f"Google News: fetched {len(g_arts)} articles")
        if g_arts:
            print(f"  Sample: {g_arts[0].title} | Source: {g_arts[0].author}")

        print("\n=== Testing MSN News Scraper ===")
        m_arts = await scrape_msn_news(client)
        print(f"MSN News: fetched {len(m_arts)} articles")
        if m_arts:
            print(f"  Sample: {m_arts[0].title} | Author: {m_arts[0].author}")

        print("\n=== Testing Yahoo News Scraper ===")
        y_arts = await scrape_yahoo_news(client)
        print(f"Yahoo News: fetched {len(y_arts)} articles")
        if y_arts:
            print(f"  Sample: {y_arts[0].title} | Author: {y_arts[0].author}")

        print("\n=== Testing X (Twitter) News Scraper ===")
        x_arts = await scrape_x_news(client)
        print(f"X News: fetched {len(x_arts)} articles")
        if x_arts:
            print(f"  Sample: {x_arts[0].title} | Author: {x_arts[0].author}")

    print("\n=== Testing Full Aggregator Refresh ===")
    start = time.time()
    await aggregator.refresh_all(force=True)
    duration = time.time() - start
    stats = aggregator.get_filter_counts()
    print(f"Aggregator refreshed in {duration:.2f}s!")
    print(f"Total articles: {stats['total_articles']}")
    print(f"Source breakdown: {stats['sources']}")
    print(f"Topic breakdown: {stats['topics']}")
    print(f"Location breakdown: {stats['locations']}")

    # Test priority feed retrieval
    priority_feed = aggregator.get_articles(topic="priority")
    print(f"\nPriority Feed returned {len(priority_feed)} sorted articles.")
    if priority_feed:
        print(f"  Top story in Priority Feed: [{priority_feed[0].topic_name}] {priority_feed[0].title} ({priority_feed[0].source_name})")

if __name__ == "__main__":
    asyncio.run(run_tests())
