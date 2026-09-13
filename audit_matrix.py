"""
Audit Matrix & QA Diagnostic Script for PulseNews
Tests all 125 combinations (5 Locations x 5 Topics x 5 Sources)
against http://localhost:8080/api/news and checks all scraper feed URLs.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import httpx
import feedparser

BASE_API_URL = "http://localhost:8080"

LOCATIONS = ["all", "bengaluru", "odisha", "india", "global"]
TOPICS = ["priority", "job_market", "technology", "entertainment", "general"]
SOURCES = ["all", "google", "msn", "yahoo", "x", "moneycontrol"]

# Raw feed definitions from scrapers
GOOGLE_QUERIES = [
    {"name": "Google - Global General", "url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "general"},
    {"name": "Google - India General", "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "general"},
    {"name": "Google - Bengaluru General", "url": "https://news.google.com/rss/search?q=Bengaluru+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "general"},
    {"name": "Google - Odisha General", "url": "https://news.google.com/rss/search?q=Odisha+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "general"},
    {"name": "Google - Bengaluru Tech", "url": "https://news.google.com/rss/search?q=Bengaluru+(tech+OR+startup+OR+AI)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "technology"},
    {"name": "Google - Bengaluru Jobs", "url": "https://news.google.com/rss/search?q=Bengaluru+(jobs+OR+hiring+OR+layoffs)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "job_market"},
    {"name": "Google - Bengaluru Entertainment", "url": "https://news.google.com/rss/search?q=Bengaluru+(movies+OR+cinema+OR+theatre+OR+entertainment)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "bengaluru", "top": "entertainment"},
    {"name": "Google - Odisha Jobs", "url": "https://news.google.com/rss/search?q=Odisha+(jobs+OR+employment+OR+industry)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "job_market"},
    {"name": "Google - Odisha Tech", "url": "https://news.google.com/rss/search?q=Odisha+(tech+OR+technology+OR+startup+OR+IT)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "technology"},
    {"name": "Google - Odisha Entertainment", "url": "https://news.google.com/rss/search?q=Odisha+(movies+OR+cinema+OR+theatre+OR+entertainment+OR+Ollywood)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "odisha", "top": "entertainment"},
    {"name": "Google - India Jobs", "url": "https://news.google.com/rss/search?q=India+(job+market+OR+hiring+OR+layoffs)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "job_market"},
    {"name": "Google - Global Tech", "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en", "loc": "global", "top": "technology"},
    {"name": "Google - Global Jobs", "url": "https://news.google.com/rss/search?q=(job+market+OR+hiring+OR+layoffs+OR+employment+trends)+when:7d&hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "job_market"},
    {"name": "Google - India Entertainment", "url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    {"name": "Google - India Cinema", "url": "https://news.google.com/rss/search?q=(Bollywood+OR+cinema+OR+movies+OR+OTT+OR+celebrity)+when:7d&hl=en-IN&gl=IN&ceid=IN:en", "loc": "india", "top": "entertainment"},
    {"name": "Google - Global Entertainment", "url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en", "loc": "global", "top": "entertainment"},
]

MSN_QUERIES = [
    {"name": "MSN - Global General", "url": "https://www.bing.com/news/search?q=world+news&format=rss", "loc": "global", "top": "general"},
    {"name": "MSN - India General", "url": "https://www.bing.com/news/search?q=india+news&format=rss", "loc": "india", "top": "general"},
    {"name": "MSN - Bengaluru General", "url": "https://www.bing.com/news/search?q=Bengaluru+Bangalore+news&format=rss", "loc": "bengaluru", "top": "general"},
    {"name": "MSN - Odisha General", "url": "https://www.bing.com/news/search?q=Odisha+Bhubaneswar+news&format=rss", "loc": "odisha", "top": "general"},
    {"name": "MSN - India Job Market", "url": "https://www.bing.com/news/search?q=job+market+employment+hiring+layoffs&format=rss", "loc": "india", "top": "job_market"},
    {"name": "MSN - Bengaluru Tech", "url": "https://www.bing.com/news/search?q=Bengaluru+tech+startups+AI&format=rss", "loc": "bengaluru", "top": "technology"},
    {"name": "MSN - Bengaluru Entertainment", "url": "https://www.bing.com/news/search?q=Bengaluru+movies+cinema+entertainment&format=rss", "loc": "bengaluru", "top": "entertainment"},
    {"name": "MSN - Odisha Job Market", "url": "https://www.bing.com/news/search?q=Odisha+jobs+employment+hiring+recruitment&format=rss", "loc": "odisha", "top": "job_market"},
    {"name": "MSN - Odisha Tech", "url": "https://www.bing.com/news/search?q=Odisha+technology+IT+startups&format=rss", "loc": "odisha", "top": "technology"},
    {"name": "MSN - Odisha Entertainment", "url": "https://www.bing.com/news/search?q=Odisha+entertainment+movies+cinema+Ollywood&format=rss", "loc": "odisha", "top": "entertainment"},
    {"name": "MSN - Global Job Market", "url": "https://www.bing.com/news/search?q=global+jobs+hiring+layoffs+careers&format=rss", "loc": "global", "top": "job_market"},
    {"name": "MSN - Global Tech", "url": "https://www.bing.com/news/search?q=technology+artificial+intelligence+tech+startups&format=rss", "loc": "global", "top": "technology"},
    {"name": "MSN - India Entertainment", "url": "https://www.bing.com/news/search?q=entertainment+movies+cinema+bollywood&format=rss", "loc": "india", "top": "entertainment"},
    {"name": "MSN - Global Entertainment", "url": "https://www.bing.com/news/search?q=hollywood+movies+entertainment+celebrity&format=rss", "loc": "global", "top": "entertainment"},
]

YAHOO_QUERIES = [
    {"name": "Yahoo - World General", "url": "https://news.yahoo.com/rss/world", "loc": "global", "top": "general"},
    {"name": "Yahoo - India General", "url": "https://news.yahoo.com/rss/india", "loc": "india", "top": "general"},
    {"name": "Yahoo - Bengaluru General", "url": "https://www.bing.com/news/search?q=site:yahoo.com+Bengaluru&format=rss", "loc": "bengaluru", "top": "general"},
    {"name": "Yahoo - Bengaluru Jobs", "url": "https://www.bing.com/news/search?q=site:yahoo.com+(Bengaluru+OR+Bangalore)+(jobs+OR+hiring+OR+careers)&format=rss", "loc": "bengaluru", "top": "job_market"},
    {"name": "Yahoo - Bengaluru Entertainment", "url": "https://www.bing.com/news/search?q=site:yahoo.com+(Bengaluru+OR+Bangalore)+(movies+OR+entertainment+OR+cinema)&format=rss", "loc": "bengaluru", "top": "entertainment"},
    {"name": "Yahoo - Odisha General", "url": "https://www.bing.com/news/search?q=site:yahoo.com+Odisha&format=rss", "loc": "odisha", "top": "general"},
    {"name": "Yahoo - Odisha Jobs", "url": "https://www.bing.com/news/search?q=site:yahoo.com+(Odisha+OR+Bhubaneswar)+(jobs+OR+employment+OR+industry)&format=rss", "loc": "odisha", "top": "job_market"},
    {"name": "Yahoo - Odisha Entertainment", "url": "https://www.bing.com/news/search?q=site:yahoo.com+(Odisha+OR+Bhubaneswar)+(movies+OR+entertainment+OR+culture)&format=rss", "loc": "odisha", "top": "entertainment"},
    {"name": "Yahoo - Top Stories / Jobs", "url": "https://finance.yahoo.com/rss/topstories", "loc": "global", "top": "job_market"},
    {"name": "Yahoo - Tech", "url": "https://news.yahoo.com/rss/tech", "loc": "global", "top": "technology"},
    {"name": "Yahoo - Entertainment", "url": "https://news.yahoo.com/rss/entertainment", "loc": "global", "top": "entertainment"},
]

X_QUERIES = [
    {"name": "X - Bengaluru General", "q": "(site:x.com OR site:twitter.com) (Bengaluru OR Bangalore)", "loc": "bengaluru", "top": "general"},
    {"name": "X - Bengaluru Tech", "q": "(site:x.com OR site:twitter.com) (Bengaluru OR Bangalore) (tech OR AI OR startup)", "loc": "bengaluru", "top": "technology"},
    {"name": "X - Bengaluru Jobs", "q": "(site:x.com OR site:twitter.com) (Bengaluru OR Bangalore) (hiring OR jobs)", "loc": "bengaluru", "top": "job_market"},
    {"name": "X - Bengaluru Entertainment", "q": "(site:x.com OR site:twitter.com) (Bengaluru OR Bangalore) (movie OR cinema OR concert OR theatre OR entertainment)", "loc": "bengaluru", "top": "entertainment"},
    {"name": "X - Odisha General", "q": "(site:x.com OR site:twitter.com) (Odisha OR Bhubaneswar)", "loc": "odisha", "top": "general"},
    {"name": "X - Odisha Jobs", "q": "(site:x.com OR site:twitter.com) (Odisha OR Bhubaneswar) (jobs OR employment)", "loc": "odisha", "top": "job_market"},
    {"name": "X - Odisha Tech", "q": "(site:x.com OR site:twitter.com) (Odisha OR Bhubaneswar) (tech OR software OR IT OR startup)", "loc": "odisha", "top": "technology"},
    {"name": "X - Odisha Entertainment", "q": "(site:x.com OR site:twitter.com) (Odisha OR Bhubaneswar) (movie OR cinema OR Ollywood OR festival)", "loc": "odisha", "top": "entertainment"},
    {"name": "X - India General", "q": "(site:x.com OR site:twitter.com) (India news OR politics OR economy)", "loc": "india", "top": "general"},
    {"name": "X - India Jobs", "q": "(site:x.com OR site:twitter.com) (hiring OR layoffs OR \"job market\" OR \"tech jobs\")", "loc": "india", "top": "job_market"},
    {"name": "X - Global Tech", "q": "(site:x.com OR site:twitter.com) (AI OR \"artificial intelligence\" OR tech OR software)", "loc": "global", "top": "technology"},
    {"name": "X - Global Jobs", "q": "(site:x.com OR site:twitter.com) (hiring OR layoffs OR \"job market\" OR \"career opportunities\")", "loc": "global", "top": "job_market"},
    {"name": "X - India Entertainment", "q": "(site:x.com OR site:twitter.com) (movie OR Bollywood OR cinema OR trailer)", "loc": "india", "top": "entertainment"},
    {"name": "X - Global Entertainment", "q": "(site:x.com OR site:twitter.com) (Hollywood OR movie trailer OR cinema OR Netflix)", "loc": "global", "top": "entertainment"},
    {"name": "X - Global General", "q": "(site:x.com OR site:twitter.com) (breaking news OR world news)", "loc": "global", "top": "general"},
]

async def audit_api_matrix(client: httpx.AsyncClient) -> Dict[str, Any]:
    print("=" * 70)
    print("AUDITING ALL 125 LOCATION x TOPIC x SOURCE COMBINATIONS VIA API")
    print("=" * 70)
    
    results = {}
    total_combinations = 0
    zero_count_combinations = []
    structure_issues = []

    for loc in LOCATIONS:
        for top in TOPICS:
            for src in SOURCES:
                total_combinations += 1
                key = f"{loc}|{top}|{src}"
                url = f"{BASE_API_URL}/api/news?location={loc}&topic={top}&source={src}&limit=200"
                try:
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code != 200:
                        results[key] = {"status": resp.status_code, "count": 0, "error": f"HTTP {resp.status_code}"}
                        zero_count_combinations.append((loc, top, src, f"HTTP Error {resp.status_code}"))
                        continue
                    
                    data = resp.json()
                    count = data.get("count", 0)
                    total_available = data.get("total_available", 0)
                    articles = data.get("articles", [])
                    results[key] = {
                        "status": 200,
                        "count": count,
                        "total_available": total_available
                    }

                    if count == 0:
                        zero_count_combinations.append((loc, top, src, "0 articles returned"))
                    else:
                        # Validate article structure on first 5 articles
                        for idx, art in enumerate(articles[:5]):
                            for field in ["id", "title", "link", "source", "location", "topic", "image_url"]:
                                val = art.get(field)
                                if not val or not str(val).strip():
                                    structure_issues.append((key, art.get("id", f"idx_{idx}"), f"Missing/empty field: {field}"))
                            
                            # Validate URL schemes
                            for ufield in ["link", "image_url"]:
                                uval = art.get(ufield, "")
                                if uval and not (uval.startswith("http://") or uval.startswith("https://")):
                                    structure_issues.append((key, art.get("id"), f"Invalid {ufield} format: {uval}"))

                except Exception as e:
                    results[key] = {"status": 0, "count": 0, "error": str(e)}
                    zero_count_combinations.append((loc, top, src, f"Exception: {e}"))

    return {
        "results": results,
        "total": total_combinations,
        "zero_count": zero_count_combinations,
        "structure_issues": structure_issues
    }

async def audit_raw_feeds(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    print("\n" + "=" * 70)
    print("AUDITING RAW SCRAPER FEEDS (HTTP STATUS, REDIRECTS, FEEDPARSER)")
    print("=" * 70)

    feed_reports = []

    # 1. Google Queries
    for q in GOOGLE_QUERIES:
        name = q["name"]
        url = q["url"]
        rep = await test_feed_url(client, "google", name, url)
        feed_reports.append(rep)

    # 2. MSN Queries
    for q in MSN_QUERIES:
        name = q["name"]
        url = q["url"]
        rep = await test_feed_url(client, "msn", name, url)
        feed_reports.append(rep)

    # 3. Yahoo Queries
    for q in YAHOO_QUERIES:
        name = q["name"]
        url = q["url"]
        rep = await test_feed_url(client, "yahoo", name, url)
        feed_reports.append(rep)

    # 4. X Queries
    for q in X_QUERIES:
        name = q["name"]
        params = httpx.URL("", params={"q": q["q"], "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}).params
        url = f"https://news.google.com/rss/search?{params}"
        rep = await test_feed_url(client, "x", name, url)
        feed_reports.append(rep)

    return feed_reports

async def test_feed_url(client: httpx.AsyncClient, source: str, name: str, url: str) -> Dict[str, Any]:
    start = time.time()
    try:
        response = await client.get(url, timeout=12.0, follow_redirects=True)
        elapsed = time.time() - start
        status_code = response.status_code
        redirect_history = [str(r.status_code) for r in response.history]

        if status_code == 200:
            feed = feedparser.parse(response.text)
            entries_count = len(feed.entries)
            feed_title = feed.feed.get("title", "Unknown Feed")
            return {
                "source": source,
                "name": name,
                "url": url,
                "status": status_code,
                "redirects": redirect_history,
                "entries": entries_count,
                "feed_title": feed_title,
                "latency_s": round(elapsed, 2),
                "healthy": entries_count > 0
            }
        else:
            return {
                "source": source,
                "name": name,
                "url": url,
                "status": status_code,
                "redirects": redirect_history,
                "entries": 0,
                "latency_s": round(elapsed, 2),
                "healthy": False,
                "error": f"HTTP {status_code}"
            }
    except Exception as e:
        return {
            "source": source,
            "name": name,
            "url": url,
            "status": 0,
            "entries": 0,
            "healthy": False,
            "error": str(e)
        }

async def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        # Check server availability first
        try:
            cfg_resp = await client.get(f"{BASE_API_URL}/api/config")
            print(f"[Init] Server connected at {BASE_API_URL}. HTTP {cfg_resp.status_code}")
        except Exception as e:
            print(f"[Error] Cannot reach server at {BASE_API_URL}: {e}")
            return

        api_audit = await audit_api_matrix(client)
        feed_audit = await audit_raw_feeds(client)

        # Output Summary
        print("\n" + "=" * 70)
        print("AUDIT SUMMARY REPORT")
        print("=" * 70)
        print(f"Total API Filter Combinations Tested: {api_audit['total']}")
        print(f"Combinations with > 0 articles: {api_audit['total'] - len(api_audit['zero_count'])}")
        print(f"Combinations with 0 articles: {len(api_audit['zero_count'])}")
        
        if api_audit['zero_count']:
            print("\nZero-Count Combinations (Location | Topic | Source):")
            for loc, top, src, reason in api_audit['zero_count']:
                print(f"  - [{loc}] [{top}] [{src}]: {reason}")

        print(f"\nStructure Issues Found: {len(api_audit['structure_issues'])}")
        for iss in api_audit['structure_issues'][:10]:
            print(f"  - {iss[0]} (ID: {iss[1]}): {iss[2]}")

        print("\nRaw Feeds Summary:")
        healthy_feeds = sum(1 for f in feed_audit if f.get("healthy"))
        print(f"  Total Feeds: {len(feed_audit)} | Healthy: {healthy_feeds} | Failing: {len(feed_audit) - healthy_feeds}")
        for f in feed_audit:
            status_symbol = "OK" if f.get("healthy") else "FAIL"
            print(f"  [{status_symbol:<4}] [{f['source'].upper():<6}] {f['name']:<30} | Status: {f.get('status')} | Entries: {f.get('entries', 0):<3} | Latency: {f.get('latency_s', 0)}s")

        # Save to json
        out_data = {
            "timestamp": time.time(),
            "api_audit": api_audit,
            "feed_audit": feed_audit
        }
        with open("audit_results.json", "w", encoding="utf-8") as out_f:
            json.dump(out_data, out_f, indent=2)
        print("\nFull audit report saved to audit_results.json")

if __name__ == "__main__":
    asyncio.run(main())
