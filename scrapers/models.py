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

    # City keyword maps: (location_id, keywords, guard_others)
    city_rules = [
        ("delhi", [
            "delhi", "new delhi", "ncr", "noida", "gurgaon", "gurugram", "faridabad",
            "ghaziabad", "dwarka", "connaught place", "janpath", "rashtrapati bhavan"
        ]),
        ("mumbai", [
            "mumbai", "bombay", "bandra", "andheri", "worli", "navi mumbai",
            "thane", "bse", "dalal street", "marine drive", "juhu", "powai"
        ]),
        ("bengaluru", [
            "bengaluru", "bangalore", "karnataka", "bmtc", "bbmp", "whitefield",
            "koramangala", "indiranagar", "mysuru", "electronic city", "sarjapur", "namma metro"
        ]),
        ("chennai", [
            "chennai", "madras", "tamil nadu", "t nagar", "anna nagar", "adyar",
            "tambaram", "velachery", "marina beach", "dmk", "aiadmk"
        ]),
        ("kolkata", [
            "kolkata", "calcutta", "west bengal", "howrah", "salt lake", "rajarhat",
            "park street", "esplanade", "jadavpur", "tollywood", "mamata", "tmc"
        ]),
        ("hyderabad", [
            "hyderabad", "telangana", "secunderabad", "hitech city", "hitec city",
            "gachibowli", "charminar", "cyberabad", "banjara hills", "madhapur"
        ]),
        ("pune", [
            "pune", "pimpri", "chinchwad", "hinjewadi", "kharadi", "viman nagar",
            "shivajinagar", "magarpatta", "hadapsar", "koregaon park"
        ]),
    ]

    # All city names for cross-guard checks
    all_city_keywords = {}
    for cid, kws in city_rules:
        all_city_keywords[cid] = kws

    # 1. Check each city
    for city_id, keywords in city_rules:
        if any(k in text for k in keywords):
            # Guard: if headline mentions another city more prominently
            other_cities_in_title = []
            for other_id, other_kws in city_rules:
                if other_id != city_id and any(k in t_lower for k in other_kws):
                    other_cities_in_title.append(other_id)
            if other_cities_in_title and not any(k in t_lower for k in keywords):
                return "india"
            return city_id

    # 2. Odisha matching
    odisha_keywords = [
        "odisha", "bhubaneswar", "cuttack", "puri", "balasore", "sambalpur",
        "mayurbhanj", "rourkela", "paradip", "chandipur", "berhampur"
    ]
    if any(k in text for k in odisha_keywords):
        other_regions = ["west bengal", "bengal", "kolkata", "bihar", "jharkhand", "assam"]
        if any(c in t_lower for c in other_regions) and not any(k in t_lower for k in odisha_keywords):
            return "india"
        return "odisha"

    # If the feed had a designated regional city default, honor it unless another city was explicitly in title
    regional_defaults = {"bengaluru", "odisha", "delhi", "mumbai", "chennai", "kolkata", "hyderabad", "pune"}
    if default in regional_defaults:
        for other_id, other_kws in city_rules:
            if other_id != default and any(k in t_lower for k in other_kws):
                return other_id
        return default

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

GARBAGE_EXACT_TITLES = {
    "news", "msn", "sports", "weather", "home", "video", "photos",
    "world", "india", "entertainment", "technology", "business",
    "lifestyle", "health", "travel", "finance", "money", "markets",
    "msn - msn", "msn - msn.com", "news - msn", "news - msn.com",
    "top stories", "top engaging news", "latest news", "breaking news",
    "yahoo mail", "- yahoo mail", "msn weather", "winter weather",
    "all games", "chennai super kings"
}

GARBAGE_SUBSTRINGS = [
    "weather radar map",
    "radar map",
    "visibility map",
    "air quality map",
    "severe weather",
    "pressure map",
    "humidity map",
    "wind map",
    "dew point map",
    "| msn weather",
    "msn weather",
    "earnings_call_transcript",
    "meta_title",
    "formatted_without_date",
    "see all racing games",
    "parking plot",
    "location details of",
    "stock quotes, business news and data",
]

def is_valid_headline(title: str, summary: str = "", link: str = "") -> bool:
    if not title:
        return False
    
    t = title.strip()
    t_lower = t.lower()
    
    # 1. Exact match against generic portal / section titles
    if t_lower in GARBAGE_EXACT_TITLES:
        return False
        
    # 2. Known garbage substrings (weather maps, internal tokens, game hubs)
    for g in GARBAGE_SUBSTRINGS:
        if g in t_lower:
            return False
            
    # 3. GPS coordinates in title (MSN weather programmatic links)
    if re.search(r"\d+\.\d+,\s*-\d+\.\d+", t):
        return False

    # 4. Currency conversion rates (e.g. '1 NZD = 0.4291 GBP', '1 AUD = 0.6175 EUR')
    if re.search(r"\b\d+(?:\.\d+)?\s*[A-Z]{3}\s*=\s*\d+(?:\.\d+)?\s*[A-Z]{3}\b", t):
        return False

    # 5. Template variables (all-caps identifier with underscores)
    if re.match(r"^[A-Z0-9_]{10,}$", t):
        return False
        
    # 6. Stock tickers / Company directory entries without a headline:
    # e.g. 'MADHAVIPL$', 'Wipro Ltd.', 'ACC Ltd.', 'Manugraph Industries Ltd.'
    if t.endswith("$") or re.match(r"^[A-Z0-9.\-_]{1,12}\$?$", t):
        return False
    if re.match(r"^[A-Za-z0-9\s.,&'-]+\s+(?:Ltd\.?|Inc\.?|Corp\.?|Plc\.?)$", t) and len(t.split()) <= 4:
        return False
    if re.match(r"^\(?\w+\)?\s+Risk$", t):
        return False

    # 7. Word count & character length heuristics:
    words = [w for w in re.split(r"\s+", t) if w]
    if len(words) < 4:
        return False
    if len(t) < 18:
        return False

    # 8. Repetitive domain / brand garbage (e.g. 'MSN - MSN', 'News MSN', etc.)
    cleaned_words = [w.lower().strip(" -–—|:.,") for w in words]
    if len(set(cleaned_words)) <= 2 and all(w in {"msn", "news", "yahoo", "com", "mail", ""} for w in cleaned_words):
        return False

    return True

