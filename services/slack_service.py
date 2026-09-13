import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from scrapers.models import NewsArticle

def sanitize_slack_text(text: str) -> str:
    """Escapes Slack special characters: &, <, >."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)  # Strip raw HTML tags
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()

def format_slack_digest_blocks(
    articles: List[NewsArticle],
    location_name: str,
    topic_name: str,
    max_items: int = 5,
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds a Slack Block Kit payload representing a multi-story news briefing.
    Includes title, summary snippet, source badges, and thumbnail image accessories.
    """
    now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    items = articles[:max_items]

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"⚡ PulseNews Briefing: {location_name} • {topic_name}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📍 *Scope:* {location_name}  |  🏷️ *Topic:* {topic_name}  |  🕒 *Generated:* {now_str}"
                }
            ]
        },
        {"type": "divider"}
    ]

    if not items:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"_No stories found matching *{location_name}* under *{topic_name}*._"
            }
        })
    else:
        for idx, art in enumerate(items):
            title = sanitize_slack_text(art.title)
            summary = sanitize_slack_text(art.summary)
            if len(summary) > 220:
                summary = summary[:217] + "..."
            
            source_name = sanitize_slack_text(art.source_name or art.source.title())
            loc_label = sanitize_slack_text(art.location_name or location_name)
            top_label = sanitize_slack_text(art.topic_name or topic_name)

            section_text = (
                f"*{idx + 1}. <{art.link}|{title}>*\n"
                f">{summary}\n"
                f"`🏢 {source_name}`  `📍 {loc_label}`  `🏷️ {top_label}`"
            )

            section_block: Dict[str, Any] = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section_text
                }
            }

            # If article has a valid web image, attach thumbnail accessory
            if art.image_url and art.image_url.startswith(("http://", "https://")):
                section_block["accessory"] = {
                    "type": "image",
                    "image_url": art.image_url,
                    "alt_text": title[:60]
                }

            blocks.append(section_block)
            if idx < len(items) - 1:
                blocks.append({"type": "divider"})

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "⚡ *PulseNews Live Aggregator* • Curated across Google News, MSN, Yahoo, X & Moneycontrol"
            }
        ]
    })

    payload: Dict[str, Any] = {
        "text": f"PulseNews Briefing: {location_name} • {topic_name} ({len(items)} stories)",
        "blocks": blocks
    }
    if channel and channel.strip():
        payload["channel"] = channel.strip()

    return payload

def format_slack_article_blocks(
    article: NewsArticle,
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds a Slack Block Kit payload for an individual news story.
    """
    title = sanitize_slack_text(article.title)
    summary = sanitize_slack_text(article.summary)
    source_name = sanitize_slack_text(article.source_name or article.source.title())
    loc_label = sanitize_slack_text(article.location_name or article.location.title())
    top_label = sanitize_slack_text(article.topic_name or article.topic.title())

    section_text = (
        f"📰 *<{article.link}|{title}>*\n"
        f">{summary}\n\n"
        f"`🏢 {source_name}`  `📍 {loc_label}`  `🏷️ {top_label}`"
    )

    section_block: Dict[str, Any] = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": section_text
        }
    }

    if article.image_url and article.image_url.startswith(("http://", "https://")):
        section_block["accessory"] = {
            "type": "image",
            "image_url": article.image_url,
            "alt_text": title[:60]
        }

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📰 PulseNews Story Dispatch",
                "emoji": True
            }
        },
        section_block,
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Shared via *PulseNews* • <{article.link}|Read Full Story on {source_name}>"
                }
            ]
        }
    ]

    payload: Dict[str, Any] = {
        "text": f"📰 {title} ({source_name})",
        "blocks": blocks
    }
    if channel and channel.strip():
        payload["channel"] = channel.strip()

    return payload

def get_lan_ip() -> str:
    """Returns local network IP address (e.g. 192.168.0.9) so phones on the same Wi-Fi can connect."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def format_slack_dashboard_blocks(
    dashboard_url: Optional[str] = None,
    channel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds a Slack Block Kit payload with the live PulseNews dashboard link,
    providing both Mobile/Wi-Fi and Computer/Local links.
    """
    lan_ip = get_lan_ip()
    port = "8080"
    mobile_url = f"http://{lan_ip}:{port}"
    local_url = f"http://localhost:{port}"

    primary_url = mobile_url if lan_ip != "127.0.0.1" else local_url

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚡ PulseNews Live Dashboard",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Your PulseNews aggregator is running and ready to open on any device!*\n\n"
                    f"📱 *Mobile & Other Devices (Same Wi-Fi):*\n"
                    f"👉 <{mobile_url}|{mobile_url}>\n\n"
                    f"💻 *Computer (Local Machine):*\n"
                    f"👉 <{local_url}|{local_url}>"
                )
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 Open Dashboard",
                    "emoji": True
                },
                "url": primary_url,
                "style": "primary"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "📍 *Locations:*\nBengaluru • Odisha • India • Global"},
                {"type": "mrkdwn", "text": "🏷️ *Topics:*\nJob Market • Technology • Entertainment • General"},
                {"type": "mrkdwn", "text": "📡 *Sources:*\nGoogle • MSN • Yahoo • X • Moneycontrol"},
                {"type": "mrkdwn", "text": f"⚡ *Network IP:*\n{lan_ip}:{port}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"💡 _Tip: Make sure your phone is connected to the same Wi-Fi network and open <{mobile_url}|{mobile_url}>._"
                }
            ]
        }
    ]

    payload: Dict[str, Any] = {
        "text": f"⚡ PulseNews Live Dashboard: {mobile_url}",
        "blocks": blocks
    }
    if channel and channel.strip():
        payload["channel"] = channel.strip()

    return payload

def send_slack_webhook(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a JSON payload to a Slack Incoming Webhook URL.
    """
    webhook_url = webhook_url.strip()
    if not webhook_url:
        return {"success": False, "error": "Slack Webhook URL is not configured."}

    if not (webhook_url.startswith("https://hooks.slack.com/") or webhook_url.startswith("https://discord.com/")):
        return {"success": False, "error": "Invalid Webhook URL. Expected format: https://hooks.slack.com/services/..."}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PulseNews-Aggregator/2.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            if resp.status == 200 and ("ok" in body.lower() or body == "ok"):
                return {"success": True, "message": "Message successfully posted to Slack!"}
            return {"success": True, "message": f"Slack responded: {body}"}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return {"success": False, "error": f"Slack API HTTP {e.code}: {err_msg}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Network connection error to Slack: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error sending to Slack: {str(e)}"}

def dispatch_slack_message(payload: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reads webhook configuration from user settings and dispatches payload to Slack.
    """
    webhook_url = settings.get("slack_webhook_url", "").strip()
    if not webhook_url:
        return {
            "success": False,
            "error": "Slack Incoming Webhook URL is not configured. Please open 'Slack Alerts' in the header to set your webhook."
        }

    channel = settings.get("slack_channel", "").strip()
    if channel and "channel" not in payload:
        payload["channel"] = channel

    return send_slack_webhook(webhook_url, payload)
