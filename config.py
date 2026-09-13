import json
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "user_settings.json"

LOCATIONS = {
    "all": {
        "id": "all",
        "name": "All Locations",
        "icon": "map-pin",
        "badge": "Everywhere"
    },
    "bengaluru": {
        "id": "bengaluru",
        "name": "Bengaluru",
        "icon": "building-2",
        "badge": "Local City"
    },
    "odisha": {
        "id": "odisha",
        "name": "Odisha",
        "icon": "landmark",
        "badge": "State / Regional"
    },
    "india": {
        "id": "india",
        "name": "India",
        "icon": "flag",
        "badge": "National"
    },
    "global": {
        "id": "global",
        "name": "Global",
        "icon": "globe",
        "badge": "Worldwide"
    }
}

TOPICS = {
    "priority": {
        "id": "priority",
        "name": "Priority Feed",
        "icon": "flame",
        "color": "#6366F1",
        "description": "Blended feed ordered according to your custom priority hierarchy"
    },
    "job_market": {
        "id": "job_market",
        "name": "Job Market",
        "icon": "briefcase",
        "color": "#10B981",
        "description": "Employment, tech hiring, layoffs, career and recruitment trends"
    },
    "technology": {
        "id": "technology",
        "name": "Technology",
        "icon": "cpu",
        "color": "#6366F1",
        "description": "AI developments, computing, startups, gadgets, software"
    },
    "entertainment": {
        "id": "entertainment",
        "name": "Entertainment",
        "icon": "film",
        "color": "#8B5CF6",
        "description": "Movies, web series, Bollywood, Hollywood, music & pop culture"
    },
    "general": {
        "id": "general",
        "name": "General News",
        "icon": "newspaper",
        "color": "#F59E0B",
        "description": "Breaking developments, politics, civic affairs, and current events"
    }
}

DEFAULT_TOPIC_PRIORITY = [
    "job_market",
    "technology",
    "entertainment",
    "general"
]

SOURCES = {
    "google": {
        "id": "google",
        "name": "Google News",
        "badge_color": "bg-blue-500/10 text-blue-400 border-blue-500/30",
        "icon": "google"
    },
    "msn": {
        "id": "msn",
        "name": "MSN News",
        "badge_color": "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        "icon": "microsoft"
    },
    "yahoo": {
        "id": "yahoo",
        "name": "Yahoo News",
        "badge_color": "bg-purple-500/10 text-purple-400 border-purple-500/30",
        "icon": "yahoo"
    },
    "x": {
        "id": "x",
        "name": "X (Twitter)",
        "badge_color": "bg-sky-500/15 text-sky-300 border-sky-500/30",
        "icon": "twitter"
    },
    "moneycontrol": {
        "id": "moneycontrol",
        "name": "Moneycontrol",
        "badge_color": "bg-amber-500/10 text-amber-400 border-amber-500/30",
        "icon": "trending-up"
    }
}

def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "priority_order" in data and isinstance(data["priority_order"], list):
                    existing = set(data["priority_order"])
                    for top in DEFAULT_TOPIC_PRIORITY:
                        if top not in existing:
                            data["priority_order"].append(top)
                    # Ensure Slack default fields exist
                    data.setdefault("slack_webhook_url", "")
                    data.setdefault("slack_channel", "")
                    data.setdefault("slack_bot_name", "PulseNews Bot")
                    return data
        except Exception:
            pass

    default_settings = {
        "priority_order": list(DEFAULT_TOPIC_PRIORITY),
        "enabled_topics": {t: True for t in DEFAULT_TOPIC_PRIORITY},
        "default_location": "all",
        "x_bearer_token": "",
        "slack_webhook_url": "",
        "slack_channel": "",
        "slack_bot_name": "PulseNews Bot"
    }
    save_settings(default_settings)
    return default_settings

def save_settings(settings: Dict[str, Any]) -> bool:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False
