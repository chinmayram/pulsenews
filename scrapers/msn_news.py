import html
import re
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image, is_valid_headline
from config import LOCATIONS, TOPICS

MSN_QUERIES = [
    # Master Feeds: Targeted fresh MSN news from last 24h, excluding weather, radars, and non-news games
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-in+(news+OR+police+OR+court+OR+government+OR+development)+-weather+-radar+-map+-forecast+-currency+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-us+(world+news+OR+international+OR+diplomacy+OR+congress)+-weather+-radar+-map+-forecast+-currency+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-in+(jobs+OR+hiring+OR+layoffs+OR+salary+OR+economy+OR+business)+-weather+-radar+-map+-currency+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-in+(technology+OR+AI+OR+\"artificial intelligence\"+OR+startup+OR+gadgets)+-weather+-radar+-map+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-in+(movie+OR+Bollywood+OR+cinema+OR+trailer+OR+celebrity)+-weather+-radar+-map+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    # Global Topics
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-us+(AI+OR+technology+OR+Apple+OR+Google+OR+Microsoft)+-weather+-radar+-map+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-us+(economy+OR+layoffs+OR+careers+OR+\"job market\")+-weather+-radar+-map+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:msn.com/en-us+(Hollywood+OR+movies+OR+celebrity+OR+Netflix)+-weather+-radar+-map+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "entertainment"},
    # Regional Metropolitan Feeds (Bing News / MSN Regional Engine with strict date sorting)
    {"url": "https://www.bing.com/news/search?q=Delhi+news&qft=sortbydate%3d%221%22&format=rss", "loc": "delhi", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Mumbai+news&qft=sortbydate%3d%221%22&format=rss", "loc": "mumbai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+news&qft=sortbydate%3d%221%22&format=rss", "loc": "bengaluru", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+tech+startups&qft=sortbydate%3d%221%22&format=rss", "loc": "bengaluru", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=Bengaluru+hiring+jobs&qft=sortbydate%3d%221%22&format=rss", "loc": "bengaluru", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=Chennai+news&qft=sortbydate%3d%221%22&format=rss", "loc": "chennai", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Kolkata+news&qft=sortbydate%3d%221%22&format=rss", "loc": "kolkata", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Hyderabad+news&qft=sortbydate%3d%221%22&format=rss", "loc": "hyderabad", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Pune+news&qft=sortbydate%3d%221%22&format=rss", "loc": "pune", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Odisha+news&qft=sortbydate%3d%221%22&format=rss", "loc": "odisha", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Bhubaneswar+news&qft=sortbydate%3d%221%22&format=rss", "loc": "odisha", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=India+breaking+news&qft=sortbydate%3d%221%22&format=rss", "loc": "india", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=India+jobs+layoffs+hiring&qft=sortbydate%3d%221%22&format=rss", "loc": "india", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=India+technology+AI+startups&qft=sortbydate%3d%221%22&format=rss", "loc": "india", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=Bollywood+movies+entertainment&qft=sortbydate%3d%221%22&format=rss", "loc": "india", "top": "entertainment"},
    {"url": "https://www.bing.com/news/search?q=Global+breaking+news&qft=sortbydate%3d%221%22&format=rss", "loc": "global", "top": "general"},
    {"url": "https://www.bing.com/news/search?q=Global+tech+Apple+OpenAI+Microsoft&qft=sortbydate%3d%221%22&format=rss", "loc": "global", "top": "technology"},
    {"url": "https://www.bing.com/news/search?q=Global+careers+hiring+economy&qft=sortbydate%3d%221%22&format=rss", "loc": "global", "top": "job_market"},
    {"url": "https://www.bing.com/news/search?q=Hollywood+movies+box+office&qft=sortbydate%3d%221%22&format=rss", "loc": "global", "top": "entertainment"},
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
    while True:
        prev = title
        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        title = re.sub(r"\s*[-–—|]?\s*MSN(?:\.com)?\s*$", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"\s*[-–—|]?\s*Bing News\s*$", "", title, flags=re.IGNORECASE).strip()
        if title == prev:
            break
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
                summary = clean_html(entry.get("summary", entry.get("description", "")))

                # Strictly validate headline quality: reject generic hub/weather/section titles
                if not is_valid_headline(title, summary, link):
                    continue

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
