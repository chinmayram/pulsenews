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

MONEYCONTROL_FEEDS = [
    # Direct Official Feeds
    {"url": "https://www.moneycontrol.com/rss/latestnews.xml", "loc": "india", "top": "general"},
    {"url": "https://www.moneycontrol.com/rss/business.xml", "loc": "india", "top": "general"},
    {"url": "https://www.moneycontrol.com/rss/economy.xml", "loc": "india", "top": "general"},
    {"url": "https://www.moneycontrol.com/rss/technology.xml", "loc": "global", "top": "technology"},
    {"url": "https://www.moneycontrol.com/rss/buzzingstocks.xml", "loc": "india", "top": "general"},

    # Targeted Regional & Topic Feeds (site:moneycontrol.com via Google News RSS)
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Delhi+OR+NCR)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "delhi", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Mumbai+OR+Bombay)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "mumbai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Bengaluru+OR+Bangalore)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Bengaluru+OR+Bangalore)+(tech+OR+startup+OR+IT)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Bengaluru+OR+Bangalore)+(jobs+OR+hiring+OR+layoffs)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Bengaluru+OR+Bangalore)+(entertainment+OR+cinema+OR+theatre)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "entertainment"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Chennai+OR+Madras)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "chennai", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Kolkata+OR+Calcutta)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "kolkata", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Hyderabad+OR+Secunderabad)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "hyderabad", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+Pune+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "pune", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Odisha+OR+Bhubaneswar+OR+Cuttack)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Odisha+OR+Bhubaneswar)+(jobs+OR+industry+OR+hiring)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Odisha+OR+Bhubaneswar)+(tech+OR+startup+OR+IT)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Odisha+OR+Bhubaneswar)+(entertainment+OR+culture+OR+heritage)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "entertainment"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(jobs+OR+hiring+OR+layoffs+OR+salary)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(tech+OR+technology+OR+AI+OR+startup)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(entertainment+OR+bollywood+OR+movies+OR+cinema)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+India+(economy+OR+markets+OR+policy+OR+business)+when:1d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(global+OR+world+OR+US+markets)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(global+tech+OR+Nvidia+OR+Apple+OR+OpenAI)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "technology"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(global+hiring+OR+layoffs+OR+jobs)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "job_market"},
    {"url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(Hollywood+OR+Oscars+OR+Netflix+OR+Marvel+OR+worldwide+box+office+OR+cinema)+when:1d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "entertainment"},
]

def clean_title(title: str) -> str:
    if not title:
        return ""
    while True:
        prev = title
        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        title = re.sub(r"\s*[-–—|]?\s*moneycontrol(?:\.com)?\s*$", "", title, flags=re.IGNORECASE).strip()
        if title == prev:
            break
    return title

def is_valid_article(title: str, link: str, summary: str = "") -> bool:
    if not is_valid_headline(title, summary, link):
        return False
    t_lower = title.lower()
    if any(p in t_lower for p in [
        "stock and share market news",
        "sensex, nifty, global market",
        "live ipo news",
        "latest & breaking news on",
        "breaking stories and articles on",
        "stock market: stock market today",
        "personal finance - moneycontrol",
        "zee entertainment enterprises - images"
    ]):
        return False
    return True


async def scrape_feed(item: dict, client: httpx.AsyncClient, limit: int = 15) -> List[NewsArticle]:
    url = item["url"]
    def_loc = item["loc"]
    def_top = item["top"]
    articles: List[NewsArticle] = []

    try:
        response = await client.get(url, timeout=12.0, follow_redirects=True)
        if response.status_code != 200:
            return []

        now = time.time()
        feed = feedparser.parse(response.text)
        for entry in feed.entries[:limit]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            clean_t = clean_title(title)
            if not is_valid_article(clean_t, link):
                continue

            # Parse summary & extract embedded image if present
            raw_summary = entry.get("summary", entry.get("description", ""))
            extracted_img = None
            clean_summary = ""

            if raw_summary:
                soup = BeautifulSoup(raw_summary, "html.parser")
                img_tag = soup.find("img")
                if img_tag and img_tag.has_attr("src"):
                    extracted_img = img_tag["src"]

                for s in soup(["script", "style", "img"]):
                    s.extract()
                clean_summary = soup.get_text(separator=" ", strip=True)
                clean_summary = html.unescape(clean_summary)
                while True:
                    prev_s = clean_summary
                    clean_summary = re.sub(r"\s*[-–—|]?\s*moneycontrol(?:\.com)?\s*$", "", clean_summary, flags=re.IGNORECASE).strip()
                    if clean_summary == prev_s:
                        break

            if not clean_summary or clean_summary.lower() == clean_t.lower():
                clean_summary = f"Latest financial, market, and business updates on {clean_t} from Moneycontrol."

            published_at = entry.get("published", "")
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

            loc = detect_location(clean_t, clean_summary, default=def_loc)
            top = detect_topic(clean_t, clean_summary, default=def_top)
            loc_name = LOCATIONS.get(loc, {}).get("name", loc.title())
            top_name = TOPICS.get(top, {}).get("name", top.title())

            article_id = NewsArticle.generate_id(clean_t, link)
            image_url = get_article_image(extracted_img, loc, top, article_id)

            articles.append(
                NewsArticle(
                    id=article_id,
                    title=clean_t,
                    link=link,
                    source="moneycontrol",
                    source_name="Moneycontrol",
                    location=loc,
                    location_name=loc_name,
                    topic=top,
                    topic_name=top_name,
                    summary=clean_summary[:280] + ("..." if len(clean_summary) > 280 else ""),
                    published_at=published_at,
                    published_relative=format_relative_time(ts),
                    timestamp=ts,
                    image_url=image_url,
                    author="Moneycontrol"
                )
            )
    except Exception as e:
        print(f"[Moneycontrol] Error fetching {url}: {e}")

    return articles

async def scrape_moneycontrol_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    all_articles = []
    for item in MONEYCONTROL_FEEDS:
        arts = await scrape_feed(item, client)
        all_articles.extend(arts)
    return all_articles
