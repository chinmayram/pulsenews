import html
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image
from config import LOCATIONS, TOPICS

MSN_QUERIES = [
    {"url": "https://www.bing.com/news/search?q=world+news&format=rss", "loc": "global", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=india+news&format=rss", "loc": "india", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+Bangalore+news&format=rss", "loc": "bengaluru", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Odisha+Bhubaneswar+news&format=rss", "loc": "odisha", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Delhi+NCR+news&format=rss", "loc": "delhi", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Mumbai+news&format=rss", "loc": "mumbai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Chennai+news&format=rss", "loc": "chennai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Kolkata+news&format=rss", "loc": "kolkata", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Hyderabad+news&format=rss", "loc": "hyderabad", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Pune+news&format=rss", "loc": "pune", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=job+market+employment+hiring+layoffs&format=rss", "loc": "india", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+tech+startups+AI&format=rss", "loc": "bengaluru", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+movies+cinema+entertainment&format=rss", "loc": "bengaluru", "top": "entertainment"},
    {"url": "https://www.bing.com/news/search?q=Odisha+jobs+employment+hiring+recruitment&format=rss", "loc": "odisha", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=Odisha+technology+IT+startups&format=rss", "loc": "odisha", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=Odisha+entertainment+movies+cinema+Ollywood&format=rss", "loc": "odisha", "top": "entertainment"},
    {"url": "https://www.bing.com/news/search?q=global+jobs+hiring+layoffs+careers&format=rss", "loc": "global", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=technology+artificial+intelligence+tech+startups&format=rss", "loc": "global", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=entertainment+movies+cinema+bollywood&format=rss", "loc": "india", "top": "entertainment"},
    {"url": "https://www.bing.com/news/search?q=hollywood+movies+entertainment+celebrity&format=rss", "loc": "global", "top": "entertainment"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

async def scrape_msn_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    articles: List[NewsArticle] = []

    for item in MSN_QUERIES:
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
                author = "MSN / Bing News"
                if "source" in entry and isinstance(entry.source, dict) and "title" in entry.source:
                    author = entry.source["title"]

                published_at = entry.get("published", "")
                ts = time.time()
                if published_at:
                    try:
                        dt = date_parser.parse(published_at)
                        ts = dt.timestamp()
                    except Exception:
                        pass

                # Extract real MSN image
                raw_image = entry.get("news_image")
                if not raw_image and "media_content" in entry and entry["media_content"]:
                    raw_image = entry["media_content"][0].get("url")

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
                        source="msn",
                        source_name="MSN News",
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
            print(f"[MSNNews] Error fetching {url}: {e}")

    return articles
