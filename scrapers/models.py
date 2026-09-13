import hashlib
import re
import time
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

FALLBACK_IMAGES = {
    ("bengaluru", "technology"): [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=600&auto=format&fit=crop&q=80"
    ],
    ("bengaluru", "job_market"): [
        "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=600&auto=format&fit=crop&q=80"
    ],
    ("bengaluru", "entertainment"): [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80"
    ],
    ("bengaluru", "general"): [
        "https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=600&auto=format&fit=crop&q=80"
    ],
    ("odisha", "general"): [
        "https://images.unsplash.com/photo-1609137144813-7d9921338f24?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?w=600&auto=format&fit=crop&q=80"
    ],
    ("odisha", "job_market"): [
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&auto=format&fit=crop&q=80"
    ],
    ("odisha", "technology"): [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=600&auto=format&fit=crop&q=80"
    ],
    ("odisha", "entertainment"): [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=600&auto=format&fit=crop&q=80"
    ],
    ("india", "general"): [
        "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1532375810709-75b1da00537c?w=600&auto=format&fit=crop&q=80"
    ],
    ("india", "job_market"): [
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&auto=format&fit=crop&q=80"
    ],
    ("india", "technology"): [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80"
    ],
    ("india", "entertainment"): [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=600&auto=format&fit=crop&q=80"
    ],
    ("global", "technology"): [
        "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80"
    ],
    ("global", "job_market"): [
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format&fit=crop&q=80"
    ],
    ("global", "entertainment"): [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=600&auto=format&fit=crop&q=80"
    ],
    ("global", "general"): [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&auto=format&fit=crop&q=80"
    ]
}

DEFAULT_FALLBACK = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&auto=format&fit=crop&q=80"

def get_article_image(existing_url: Optional[str], location: str, topic: str, article_id: str) -> str:
    if existing_url and isinstance(existing_url, str) and existing_url.startswith("http"):
        # Upgrade http to https to avoid mixed-content issues
        if existing_url.startswith("http://"):
            return "https://" + existing_url[7:]
        return existing_url

    pool = FALLBACK_IMAGES.get((location, topic))
    if not pool:
        pool = FALLBACK_IMAGES.get((location, "general"))
    if not pool:
        pool = FALLBACK_IMAGES.get(("global", topic))
    if not pool:
        return DEFAULT_FALLBACK

    # Deterministic hash pick
    idx = int(hashlib.md5(article_id.encode()).hexdigest(), 16) % len(pool)
    return pool[idx]

class NewsArticle(BaseModel):
    id: str
    title: str
    link: str
    source: str  # 'google', 'msn', 'yahoo', 'x'
    source_name: str
    location: str  # 'bengaluru', 'odisha', 'india', 'global'
    location_name: str
    topic: str     # 'job_market', 'technology', 'entertainment', 'general'
    topic_name: str
    summary: str
    published_at: Optional[str] = None
    published_relative: str = "Recently"
    timestamp: float = Field(default_factory=time.time)
    image_url: Optional[str] = None
    author: Optional[str] = None

    @classmethod
    def generate_id(cls, title: str, link: str) -> str:
        content = f"{title.strip().lower()}_{link.strip()}".encode("utf-8")
        return hashlib.md5(content).hexdigest()[:12]

def detect_location(title: str, summary: str, default: str = "global") -> str:
    text = f"{title} {summary}".lower()
    t_lower = title.lower()

    # 1. Direct Bengaluru / Karnataka matching
    beng_keywords = [
        "bengaluru", "bangalore", "karnataka", "bmtc", "bbmp", "whitefield",
        "koramangala", "indiranagar", "mysuru", "electronic city", "sarjapur", "namma metro"
    ]
    if any(k in text for k in beng_keywords):
        # Guard: If headline is primarily about another city/state and does not mention Bengaluru in title
        other_cities = ["hyderabad", "telangana", "kolkata", "west bengal", "mumbai", "delhi", "chennai", "pune", "gujarat"]
        if any(c in t_lower for c in other_cities) and not any(k in t_lower for k in beng_keywords):
            return "india"
        return "bengaluru"

    # 2. Direct Odisha matching
    odisha_keywords = [
        "odisha", "bhubaneswar", "cuttack", "puri", "balasore", "sambalpur",
        "mayurbhanj", "rourkela", "paradip", "chandipur", "berhampur"
    ]
    if any(k in text for k in odisha_keywords):
        # Guard: If headline is primarily about another state and does not mention Odisha in title
        other_regions = ["west bengal", "bengal", "kolkata", "bihar", "jharkhand", "assam"]
        if any(c in t_lower for c in other_regions) and not any(k in t_lower for k in odisha_keywords):
            return "india"
        return "odisha"

    # If default was regional but article doesn't match regional keywords at all:
    if default in ("bengaluru", "odisha"):
        return "india"

    # 3. Global detection
    if default == "global":
        if any(k in text for k in ["global", "world", "worldwide", "international", "hollywood", "oscars", "us", "u.s.", "fed", "wall street", "disney", "netflix", "marvel", "europe", "china", "uk"]):
            return "global"
        if not any(k in text for k in ["delhi", "mumbai", "modi", "lok sabha", "parliament", "rbi"]):
            return "global"

    # 4. India detection
    if any(k in text for k in ["india", "delhi", "mumbai", "modi", "rupee", "isro", "lok sabha", "parliament", "rbi"]):
        return "india"

    return default

def detect_topic(title: str, summary: str, default: str = "general") -> str:
    # If the feed source is already explicitly dedicated to a topic, honor it
    if default in ("entertainment", "job_market", "technology"):
        return default

    text = f"{title} {summary}".lower()
    # Job Market
    if any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in [
        "job", "jobs", "hiring", "layoff", "layoffs", "career", "salary", "recruitment", "vacancy", "internship", "employment", "unemployment", "resignation"
    ]):
        return "job_market"

    # Technology
    if any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in [
        "ai", "tech", "technology", "software", "startup", "startups", "robot", "robotics", "cloud", "chip", "chips", "semiconductor", "nvidia", "apple", "google", "openai", "anthropic", "meta", "crypto", "cyber", "hardware", "gadget", "gadgets", "smartphone", "algorithm"
    ]):
        return "technology"

    # Entertainment
    if any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in [
        "movie", "movies", "film", "films", "cinema", "actor", "actress", "bollywood", "hollywood", "trailer", "box office", "song", "album", "ott", "series", "theatre", "entertainment", "celebrity", "superstar"
    ]):
        return "entertainment"

    return default

def format_relative_time(timestamp: float) -> str:
    now = time.time()
    diff = max(0, int(now - timestamp))
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        mins = diff // 60
        return f"{mins}m ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours}h ago"
    elif diff < 604800:
        days = diff // 86400
        return f"{days}d ago"
    else:
        return datetime.fromtimestamp(timestamp).strftime("%b %d, %Y")
