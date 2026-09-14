import html
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image
from config import LOCATIONS, TOPICS

YAHOO_QUERIES = [
    {"url": "https://news.yahoo.com/rss/world", "loc": "global", "top": "general"},
    {"url": "https://news.yahoo.com/rss/india", "loc": "india", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Delhi+NCR&format=rss", "loc": "delhi", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Mumbai&format=rss", "loc": "mumbai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Bengaluru&format=rss", "loc": "bengaluru", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+(Bengaluru+OR+Bangalore)+(jobs+OR+hiring+OR+careers)&format=rss", "loc": "bengaluru", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+(Bengaluru+OR+Bangalore)+(movies+OR+entertainment+OR+cinema)&format=rss", "loc": "bengaluru", "top": "entertainment"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Chennai&format=rss", "loc": "chennai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Kolkata&format=rss", "loc": "kolkata", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Hyderabad&format=rss", "loc": "hyderabad", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Pune&format=rss", "loc": "pune", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+Odisha&format=rss", "loc": "odisha", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+(Odisha+OR+Bhubaneswar)+(jobs+OR+employment+OR+industry)&format=rss", "loc": "odisha", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=site:yahoo.com+(Odisha+OR+Bhubaneswar)+(movies+OR+entertainment+OR+culture)&format=rss", "loc": "odisha", "top": "entertainment"},
    {"url": "https://finance.yahoo.com/rss/topstories", "loc": "global", "top": "job_market"},
    {"url": "https://news.yahoo.com/rss/tech", "loc": "global", "top": "technology"},
    {"url": "https://news.yahoo.com/rss/entertainment", "loc": "global", "top": "entertainment"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

async def scrape_yahoo_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    articles: List[NewsArticle] = []

    for item in YAHOO_QUERIES:
        url = item["url"]
        def_loc = item["loc"]
        def_top = item["top"]
        try:
            response = await client.get(url, timeout=12.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            feed = feedparser.parse(response.text)
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue

                summary = clean_html(entry.get("summary", entry.get("description", "")))
                author = "Yahoo News"
                if "source" in entry and isinstance(entry.source, dict) and "title" in entry.source:
                    author = entry.source["title"]

                published_at = entry.get("published", "")
                now = time.time()
                ts = now
                if published_at:
                    try:
                        dt = date_parser.parse(published_at)
                        ts = dt.timestamp()
                    except Exception:
                        pass

                # Only allow news from last 24 hours
                if (now - ts) > (24 * 3600):
                    continue

                # Extract real Yahoo image
                raw_image = None
                if "media_content" in entry and entry["media_content"]:
                    raw_image = entry["media_content"][0].get("url")
                elif "news_image" in entry and entry.get("news_image"):
                    raw_image = entry.get("news_image")

                loc = detect_location(title, summary, default=def_loc)
                top = detect_topic(title, summary, default=def_top)
                loc_name = LOCATIONS.get(loc, {}).get("name", loc.title())
                top_name = TOPICS.get(top, {}).get("name", top.title())

                article_id = NewsArticle.generate_id(title, link)
                image_url = get_article_image(raw_image, loc, top, article_id)

                articles.append(
                    NewsArticle(
                        id=article_id,
                        title=title,
                        link=link,
                        source="yahoo",
                        source_name="Yahoo News",
                        location=loc,
                        location_name=loc_name,
                        topic=top,
                        topic_name=top_name,
                        summary=summary[:280] + ("..." if len(summary) > 280 else ""),
                        published_at=published_at,
                        published_relative=format_relative_time(ts),
                        timestamp=ts,
                        image_url=image_url,
                        author=author
                    )
                )
        except Exception as e:
            print(f"[YahooNews] Error fetching {url}: {e}")

    return articles
