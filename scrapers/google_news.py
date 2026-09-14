import html
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image
from config import LOCATIONS, TOPICS

GOOGLE_QUERIES = [
    {"url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    {"url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    # Bengaluru
    {"url": "https://news.google.com/rss/search?q=Bengaluru+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Bengaluru+(tech+OR+startup+OR+AI)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=Bengaluru+(jobs+OR+hiring+OR+layoffs)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=Bengaluru+(movies+OR+cinema+OR+theatre+OR+entertainment)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "entertainment"},
    # Odisha
    {"url": "https://news.google.com/rss/search?q=Odisha+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Odisha+(jobs+OR+employment+OR+industry)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=Odisha+(tech+OR+technology+OR+startup+OR+IT)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=Odisha+(movies+OR+cinema+OR+theatre+OR+entertainment+OR+Ollywood)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "entertainment"},
    # Delhi NCR
    {"url": "https://news.google.com/rss/search?q=Delhi+NCR+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "delhi", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Delhi+(tech+OR+startup+OR+AI)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "delhi", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=Delhi+(jobs+OR+hiring+OR+layoffs)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "delhi", "top": "job_market"},
    # Mumbai
    {"url": "https://news.google.com/rss/search?q=Mumbai+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "mumbai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Mumbai+(tech+OR+startup+OR+fintech)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "mumbai", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=Mumbai+(Bollywood+OR+movies+OR+cinema+OR+entertainment)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "mumbai", "top": "entertainment"},
    # Chennai
    {"url": "https://news.google.com/rss/search?q=Chennai+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "chennai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Chennai+(tech+OR+IT+OR+startup)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "chennai", "top": "technology"},
    # Kolkata
    {"url": "https://news.google.com/rss/search?q=Kolkata+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "kolkata", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Kolkata+(tech+OR+IT+OR+startup)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "kolkata", "top": "technology"},
    # Hyderabad
    {"url": "https://news.google.com/rss/search?q=Hyderabad+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "hyderabad", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Hyderabad+(tech+OR+IT+OR+startup+OR+AI)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "hyderabad", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=Hyderabad+(Tollywood+OR+movies+OR+cinema+OR+entertainment)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "hyderabad", "top": "entertainment"},
    # Pune
    {"url": "https://news.google.com/rss/search?q=Pune+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "pune", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=Pune+(tech+OR+IT+OR+startup)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "pune", "top": "technology"},
    # National & Global topic feeds
    {"url": "https://news.google.com/rss/search?q=India+(job+market+OR+hiring+OR+layoffs)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "job_market"},
    {"url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en", "loc": "global", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=(job+market+OR+hiring+OR+layoffs+OR+employment+trends)+when:7d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "job_market"},
    {"url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    {"url": "https://news.google.com/rss/search?q=(Bollywood+OR+cinema+OR+movies+OR+OTT+OR+celebrity)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    {"url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "entertainment"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

async def scrape_google_news_feed(item: dict, client: httpx.AsyncClient, limit: int = 15) -> List[NewsArticle]:
    url = item["url"]
    def_loc = item["loc"]
    def_top = item["top"]
    articles: List[NewsArticle] = []

    try:
        response = await client.get(url, timeout=12.0, follow_redirects=True)
        if response.status_code != 200:
            return []

        feed = feedparser.parse(response.text)
        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            author = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                author = parts[1].strip()

            summary = clean_html(entry.get("summary", entry.get("description", "")))
            if not summary or summary == title:
                summary = f"Latest report from {author} via Google News."

            published_at = entry.get("published", "")
            ts = time.time()
            if published_at:
                try:
                    dt = date_parser.parse(published_at)
                    ts = dt.timestamp()
                except Exception:
                    pass

            loc = detect_location(title, summary, default=def_loc)
            top = detect_topic(title, summary, default=def_top)
            loc_name = LOCATIONS.get(loc, {}).get("name", loc.title())
            top_name = TOPICS.get(top, {}).get("name", top.title())

            article_id = NewsArticle.generate_id(title, link)
            image_url = get_article_image(None, loc, top, article_id)

            articles.append(
                NewsArticle(
                    id=article_id,
                    title=title,
                    link=link,
                    source="google",
                    source_name="Google News",
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
        print(f"[GoogleNews] Error fetching {url}: {e}")

    return articles

async def scrape_google_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    all_articles = []
    for item in GOOGLE_QUERIES:
        arts = await scrape_google_news_feed(item, client)
        all_articles.extend(arts)
    return all_articles
