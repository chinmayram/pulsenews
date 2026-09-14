import html
import re
import time
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
import httpx

from scrapers.models import NewsArticle, format_relative_time, detect_location, detect_topic, get_article_image
from config import LOCATIONS, TOPICS, load_settings

X_QUERIES = [
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Delhi OR \"New Delhi\" OR NCR)", "loc": "delhi", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Mumbai OR Bombay)", "loc": "mumbai", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Bengaluru OR Bangalore)", "loc": "bengaluru", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Bengaluru OR Bangalore) (tech OR AI OR startup)", "loc": "bengaluru", "top": "technology"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Bengaluru OR Bangalore) (hiring OR jobs)", "loc": "bengaluru", "top": "job_market"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Bengaluru OR Bangalore) (movie OR cinema OR concert OR theatre OR entertainment)", "loc": "bengaluru", "top": "entertainment"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Chennai OR Madras)", "loc": "chennai", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Kolkata OR Calcutta)", "loc": "kolkata", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Hyderabad OR Secunderabad)", "loc": "hyderabad", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) Pune", "loc": "pune", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Odisha OR Bhubaneswar)", "loc": "odisha", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Odisha OR Bhubaneswar) (jobs OR employment)", "loc": "odisha", "top": "job_market"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Odisha OR Bhubaneswar) (tech OR software OR IT OR startup)", "loc": "odisha", "top": "technology"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Odisha OR Bhubaneswar) (movie OR cinema OR Ollywood OR festival)", "loc": "odisha", "top": "entertainment"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (India news OR politics OR economy)", "loc": "india", "top": "general"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (hiring OR layoffs OR \"job market\" OR \"tech jobs\")", "loc": "india", "top": "job_market"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (AI OR \"artificial intelligence\" OR tech OR software)", "loc": "global", "top": "technology"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (hiring OR layoffs OR \"job market\" OR \"career opportunities\")", "loc": "global", "top": "job_market"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (movie OR Bollywood OR cinema OR trailer)", "loc": "india", "top": "entertainment"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (Hollywood OR movie trailer OR cinema OR Netflix)", "loc": "global", "top": "entertainment"},
    {"q": "(site:x.com/*/status OR site:twitter.com/*/status) (breaking news OR world news)", "loc": "global", "top": "general"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    return html.unescape(text)

def clean_x_title(raw_title: str) -> str:
    title = re.sub(r'\s*-\s*(x\.com|twitter\.com)\s*$', '', raw_title.strip(), flags=re.IGNORECASE)
    return title.strip()

def is_valid_news_tweet(title: str) -> bool:
    """Rejects profile/channel page entries, raw URLs, or short non-news strings."""
    t = title.strip()
    if t.startswith("https://t.co") or t.startswith("http://t.co"):
        return False
    # Matches channel accounts like 'TIMES NOW (@TimesNow)', 'Rishabh Singh (@merishabh_singh)', etc.
    if re.search(r'^\s*[^()]{1,60}\s*\(@[A-Za-z0-9_]{1,30}\)(\s+on\s+X)?\s*$', t, re.IGNORECASE):
        return False
    # Must have reasonable sentence length
    if len(t) < 22 or len(t.split()) < 4:
        return False
    return True

def extract_x_author(text: str) -> str:
    handles = re.findall(r'@([A-Za-z0-9_]{1,20})', text)
    if handles:
        return f"@{handles[0]} on X"
    if text.startswith("#WATCH"):
        return "Video on X"
    return "Trending on X"

async def scrape_x_news(client: httpx.AsyncClient) -> List[NewsArticle]:
    articles: List[NewsArticle] = []

    for item in X_QUERIES:
        q = f"{item['q']} when:1d"
        def_loc = item["loc"]
        def_top = item["top"]
        encoded = httpx.URL("", params={"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}).params
        url = f"https://news.google.com/rss/search?{encoded}"

        try:
            response = await client.get(url, timeout=12.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            now = time.time()
            feed = feedparser.parse(response.text)
            for entry in feed.entries[:15]:
                raw_title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not raw_title or not link:
                    continue

                clean_title = clean_x_title(raw_title)
                if not is_valid_news_tweet(clean_title):
                    continue
                summary = clean_html(entry.get("summary", entry.get("description", "")))
                if not summary or summary == raw_title:
                    summary = clean_title

                author = extract_x_author(clean_title)

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

                loc = detect_location(clean_title, summary, default=def_loc)
                top = detect_topic(clean_title, summary, default=def_top)
                loc_name = LOCATIONS.get(loc, {}).get("name", loc.title())
                top_name = TOPICS.get(top, {}).get("name", top.title())

                article_id = NewsArticle.generate_id(clean_title, link)
                # Twitter social visual or category image
                image_url = get_article_image(None, loc, top, article_id)

                articles.append(
                    NewsArticle(
                        id=article_id,
                        title=clean_title,
                        link=link,
                        source="x",
                        source_name="X (Twitter)",
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
            print(f"[XNews] Error fetching {q}: {e}")

    return articles
