import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from config import LOCATIONS, TOPICS, SOURCES, load_settings, save_settings
from scrapers.aggregator import aggregator
from services.slack_service import (
    format_slack_digest_blocks,
    format_slack_article_blocks,
    format_slack_dashboard_blocks,
    dispatch_slack_message
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

class PriorityUpdateRequest(BaseModel):
    priority_order: List[str]
    enabled_topics: Optional[Dict[str, bool]] = None
    x_bearer_token: Optional[str] = None

class SlackSettingsRequest(BaseModel):
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_bot_name: Optional[str] = "PulseNews Bot"

class SendArticleSlackRequest(BaseModel):
    title: str
    link: str
    summary: Optional[str] = ""
    source: Optional[str] = "news"
    source_name: Optional[str] = ""
    location: Optional[str] = "all"
    location_name: Optional[str] = ""
    topic: Optional[str] = "general"
    topic_name: Optional[str] = ""
    image_url: Optional[str] = None
    channel: Optional[str] = None

class SendDigestRequest(BaseModel):
    location: Optional[str] = "all"
    topic: Optional[str] = "priority"
    source: Optional[str] = "all"
    limit: Optional[int] = 5

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting News Aggregator Server... Triggering initial scrape.")
    asyncio.create_task(aggregator.refresh_all(force=True))
    yield
    print("Shutting down News Aggregator Server.")

app = FastAPI(
    title="PulseNews Multi-Source Aggregator",
    description="Live news scraping across Google, MSN, Yahoo, and X with interactive Location, Topic, and Source filters.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

@app.get("/")
async def root():
    index_file = BASE_DIR / "index.html"
    if not index_file.exists():
        index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "News Aggregator API is running. UI not found."}

@app.get("/api/news")
async def get_news(
    location: str = Query("all", description="Location: 'all', 'bengaluru', 'odisha', 'india', 'global'"),
    topic: str = Query("priority", description="Topic: 'priority', 'job_market', 'technology', 'entertainment', 'general'"),
    source: str = Query("all", description="Source: 'all', 'google', 'msn', 'yahoo', 'x'"),
    search: Optional[str] = Query(None, description="Keyword search query"),
    limit: int = Query(150, ge=1, le=500)
):
    if not aggregator.articles:
        await aggregator.refresh_all(force=False)

    articles = aggregator.get_articles(
        location=location,
        topic=topic,
        source=source,
        search_query=search
    )
    paginated = articles[:limit]

    # Calculate reactive dynamic counts across all 3 dimensions
    filter_counts = aggregator.get_filter_counts(
        active_location=location,
        active_topic=topic,
        active_source=source,
        search_query=search
    )

    return {
        "articles": paginated,
        "count": len(paginated),
        "total_available": len(articles),
        "active_location": location,
        "active_topic": topic,
        "active_source": source,
        "filter_counts": filter_counts,
        "last_refreshed": filter_counts["last_refreshed"],
        "is_refreshing": filter_counts["is_refreshing"]
    }

@app.api_route("/api/news/refresh", methods=["GET", "POST", "HEAD"])
async def refresh_news():
    try:
        articles = await aggregator.refresh_all(force=True)
        counts = aggregator.get_filter_counts()
        return {
            "status": "success",
            "message": f"Successfully refreshed {len(articles)} news articles across all 5 sources.",
            "stats": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@app.get("/api/config")
async def get_config():
    settings = load_settings()
    counts = aggregator.get_filter_counts()

    return {
        "locations": LOCATIONS,
        "topics": TOPICS,
        "sources": SOURCES,
        "priority_order": settings.get("priority_order", []),
        "enabled_topics": settings.get("enabled_topics", {}),
        "filter_counts": counts
    }

@app.post("/api/priority")
async def update_priority(req: PriorityUpdateRequest):
    settings = load_settings()
    valid_topics = [t for t in req.priority_order if t in TOPICS and t != "priority"]
    for t in TOPICS.keys():
        if t != "priority" and t not in valid_topics:
            valid_topics.append(t)

    settings["priority_order"] = valid_topics
    if req.enabled_topics is not None:
        settings["enabled_topics"] = req.enabled_topics
    if req.x_bearer_token is not None:
        settings["x_bearer_token"] = req.x_bearer_token.strip()

    save_settings(settings)
    return {
        "status": "success",
        "message": "Topic priority settings updated successfully.",
        "settings": settings
    }

@app.get("/api/stats")
async def get_stats():
    return aggregator.get_filter_counts()

@app.get("/api/slack/config")
async def get_slack_config():
    settings = load_settings()
    webhook = settings.get("slack_webhook_url", "").strip()
    masked_webhook = ""
    if webhook:
        if len(webhook) > 36:
            masked_webhook = webhook[:33] + "..." + webhook[-4:]
        else:
            masked_webhook = "****"

    return {
        "slack_webhook_url_masked": masked_webhook,
        "has_webhook": bool(webhook),
        "slack_channel": settings.get("slack_channel", ""),
        "slack_bot_name": settings.get("slack_bot_name", "PulseNews Bot")
    }

@app.post("/api/slack/config")
async def update_slack_config(req: SlackSettingsRequest):
    settings = load_settings()
    if req.slack_webhook_url is not None:
        url = req.slack_webhook_url.strip()
        if url and not (url.startswith("https://hooks.slack.com/") or url.startswith("https://discord.com/")):
            raise HTTPException(status_code=400, detail="Invalid Webhook URL. It must start with https://hooks.slack.com/")
        if not url.startswith("****"):
            settings["slack_webhook_url"] = url
    if req.slack_channel is not None:
        settings["slack_channel"] = req.slack_channel.strip()
    if req.slack_bot_name is not None:
        settings["slack_bot_name"] = req.slack_bot_name.strip()

    save_settings(settings)
    return {"status": "success", "message": "Slack configuration saved successfully."}

@app.post("/api/slack/send_digest")
async def send_slack_digest_endpoint(req: SendDigestRequest):
    settings = load_settings()
    if not settings.get("slack_webhook_url"):
        raise HTTPException(
            status_code=400,
            detail="Slack Webhook URL is not configured. Please open 'Slack Alerts' in the navigation bar to configure your webhook."
        )

    articles = aggregator.get_articles(
        location=req.location,
        topic=req.topic,
        source=req.source
    )
    loc_name = LOCATIONS.get(req.location, {}).get("name", req.location.title())
    top_name = TOPICS.get(req.topic, {}).get("name", req.topic.title())

    payload = format_slack_digest_blocks(
        articles=articles,
        location_name=loc_name,
        topic_name=top_name,
        max_items=req.limit or 5,
        channel=settings.get("slack_channel")
    )

    result = dispatch_slack_message(payload, settings)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send Slack message"))

    dest = settings.get("slack_channel") or "default webhook channel"
    return {
        "status": "success",
        "message": f"Slack digest for {loc_name} • {top_name} successfully sent to {dest}!"
    }

@app.post("/api/slack/send_dashboard")
async def send_slack_dashboard_endpoint():
    settings = load_settings()
    if not settings.get("slack_webhook_url"):
        raise HTTPException(
            status_code=400,
            detail="Slack Webhook URL is not configured. Please open 'Slack Alerts' in the navigation bar to configure your webhook."
        )

    payload = format_slack_dashboard_blocks(
        dashboard_url="http://localhost:8080",
        channel=settings.get("slack_channel")
    )

    result = dispatch_slack_message(payload, settings)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send dashboard link to Slack"))

    dest = settings.get("slack_channel") or "default channel"
    return {
        "status": "success",
        "message": f"Dashboard link successfully sent to Slack ({dest})!"
    }

@app.post("/api/slack/send_article")
async def send_slack_article_endpoint(req: SendArticleSlackRequest):
    settings = load_settings()
    if not settings.get("slack_webhook_url"):
        raise HTTPException(
            status_code=400,
            detail="Slack Webhook URL is not configured. Please open 'Slack Alerts' in the navigation bar to configure your webhook."
        )

    import hashlib
    from scrapers.models import NewsArticle
    article = NewsArticle(
        id=hashlib.md5(req.link.encode()).hexdigest(),
        title=req.title,
        link=req.link,
        summary=req.summary or "",
        source=req.source or "news",
        source_name=req.source_name or (req.source.title() if req.source else "News"),
        location=req.location or "all",
        location_name=req.location_name or "All",
        topic=req.topic or "general",
        topic_name=req.topic_name or "General",
        image_url=req.image_url
    )

    payload = format_slack_article_blocks(
        article=article,
        channel=req.channel or settings.get("slack_channel")
    )

    result = dispatch_slack_message(payload, settings)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send article to Slack"))

    return {
        "status": "success",
        "message": f"Article sent to Slack: {article.title[:45]}..."
    }

@app.post("/api/slack/test")
async def test_slack_connection():
    settings = load_settings()
    webhook = settings.get("slack_webhook_url", "").strip()
    if not webhook:
        raise HTTPException(status_code=400, detail="Please enter and save a valid Slack Webhook URL first.")

    test_payload = {
        "text": "👋 PulseNews Slack Integration Test",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎉 PulseNews Slack Connected!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Your PulseNews Slack integration is working perfectly!\n\nYou can now dispatch live multi-source news briefings and individual breaking stories directly to your channels.\n\n`Google News` • `MSN News` • `Yahoo News` • `X (Twitter)` • `Moneycontrol`"
                }
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "⚡ *PulseNews Live Multi-Source Aggregator* • Test verified"
                    }
                ]
            }
        ]
    }
    result = dispatch_slack_message(test_payload, settings)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Test message failed to reach Slack"))
    return {"status": "success", "message": "Test verification message posted to Slack!"}

if __name__ == "__main__":
    import uvicorn
    import socket

    def is_port_free(p: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', p))
                return True
        except Exception:
            return False

    target_port = 8000 if is_port_free(8000) else 8080
    print(f"Starting PulseNews server on http://localhost:{target_port} ...")
    uvicorn.run("main:app", host="0.0.0.0", port=target_port, reload=False)
