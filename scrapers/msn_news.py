import html
import re
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image
from config import LOCATIONS, TOPICS

MSN_QUERIES = [
    # Master Feed: All fresh MSN articles from last 24h
    {"url": "https://news.google.com/rss/search?q=site:msn.com+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    # Metros & States
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Delhi+OR+NCR)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "delhi", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Mumbai+OR+Bombay)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "mumbai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Bengaluru+OR+Bangalore)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Bengaluru+OR+Bangalore)+(tech+OR+AI+OR+startup)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Bengaluru+OR+Bangalore)+(jobs+OR+hiring+OR+careers)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Chennai+OR+Madras)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "chennai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Kolkata+OR+Calcutta)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "kolkata", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Hyderabad+OR+Secunderabad)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "hyderabad", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+Pune+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "pune", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Odisha+OR+Bhubaneswar+OR+Cuttack)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Odisha+OR+Bhubaneswar)+(jobs+OR+hiring+OR+employment)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Odisha+OR+Bhubaneswar)+(tech+OR+IT+OR+software)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Odisha+OR+Bhubaneswar)+(movie+OR+cinema+OR+culture)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "entertainment"},
    # National & Topics
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(India+news+OR+national+OR+politics+OR+economy)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(jobs+OR+hiring+OR+layoffs+OR+salary+OR+\"job market\")+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(technology+OR+AI+OR+\"artificial intelligence\"+OR+startup)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(movie+OR+Bollywood+OR+cinema+OR+trailer+OR+box+office)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    # Global
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(world+news+OR+international+OR+global)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(global+tech+OR+Apple+OR+Google+OR+Microsoft+OR+AI)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(global+hiring+OR+layoffs+OR+careers)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com+(Hollywood+OR+movies+OR+celebrity+OR+Netflix)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "entertainment"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

def clean_title(title: str) -> str:
    if not title:
        return ""
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    title = re.sub(r"\s*[-–—|]?\s*MSN(?:\.com)?\s*$", "", title, flags=re.IGNORECASE).strip()
    return title

async def scrape_msn_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    articles: List[NewsArticle] = []
    seen_ids = set()

    for item in MSN_QUERIES:
        url = item["url"]
        def_loc = item["loc"]
        def_top = item["top"]
        try:
            response = await client.get(url, timeout=12.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            now = time.time()
            feed = feedparser.parse(response.text)
            for entry in feed.entries[:40]:
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not raw_title or not link:
                    continue

                title = clean_title(raw_title)
                if not title:
                    title = raw_title

                summary = clean_html(entry.get("summary", entry.get("description", "")))
                author = "MSN News"
                if "source" in entry and isinstance(entry.source, dict) and "title" in entry.source:
                    author = entry.source["title"]

                published_at = entry.get("published", "")
                ts = now
                if published_at:
                    try:
                        dt = date_parser.parse(published_at)
                        ts = dt.timestamp()
                    except Exception:
                        pass

                # Strictly enforce 24-hour cutoff
                if (now - ts) > (24 * 3600):
                    continue

                # Extract image
                raw_image = entry.get("news_image")
                if not raw_image and "media_content" in entry and entry["media_content"]:
                    raw_image = entry["media_content"][0].get("url")

                loc = detect_location(title, summary, default=def_loc)
                top = detect_topic(title, summary, default=def_top)
                loc_name = LOCATIONS.get(loc, {}).get("name", loc.title())
                top_name = TOPICS.get(top, {}).get("name", top.title())

                article_id = NewsArticle.generate_id(title, link)
                if article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

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
