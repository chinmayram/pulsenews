# PulseNews: Multi-Source News Aggregator & Live Dashboard

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-GitHub%20Pages-6366F1?style=for-the-badge&logo=github)](https://chinmayram.github.io/pulsenews/)
[![Auto Scraping](https://img.shields.io/badge/Auto%20Scrape-Every%202%20Hours-10B981?style=for-the-badge&logo=githubactions)](https://github.com/chinmayram/pulsenews/actions)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://python.org)

🌐 **Live Web & Mobile Dashboard**:  
👉 **[https://chinmayram.github.io/pulsenews/](https://chinmayram.github.io/pulsenews/)**

PulseNews is an ultra-fast news aggregator and live scraping dashboard that aggregates, parses, deduplicates, and organizes news across **Google News**, **MSN News**, **Yahoo News**, **Verified X (Twitter)**, and **Moneycontrol** into an interactive 3-tier matrix with responsive mobile support, automated GitHub Actions builds, and Slack alerts.

---

## 🌟 Key Features

1. **Multi-Source Scraping (5 Engines)**:
   - 🔵 **Google News**: Real-time RSS feeds, top stories, and specialized keyword queries.
   - 🟢 **MSN News**: Bing & MSN News topic feeds.
   - 🟣 **Yahoo News**: Yahoo World, Finance, and regional news feeds.
   - 🐦 **Verified X (Twitter)**: News accounts, social trends, and real-time community discussions.
   - 🟡 **Moneycontrol**: Verified Indian business, markets, startups, tech, and location-specific feeds.

2. **3-Tier Interactive Filter Architecture**:
   - **Locations**: All Locations, Bengaluru, Odisha, India, Global.
   - **Topics**: Priority Feed, Job Market, Technology, Entertainment, General News.
   - **Sources**: All Sources, Google News, MSN, Yahoo, X, Moneycontrol.
   - Cross-filtering with real-time reactive counts on every chip.

3. **Dual-Mode Deployment**:
   - **GitHub Pages Static Mode**: Zero server cost, zero downtime, instant client-side filtering from pre-rendered data/news.json. Accessible from any mobile device, tablet, or desktop anywhere in the world.
   - **FastAPI Live Server Mode**: Local or Cloud Python backend (main.py) with real-time asynchronous multi-source scraping and REST API.

4. **Automated GitHub Actions**:
   - Every 2 hours, GitHub Actions automatically executes export_news.py, scrapes all 5 sources in parallel, and redeploys fresh articles to GitHub Pages without manual intervention.

5. **Slack & WhatsApp Integrations**:
   - Send live dashboard link directly to Slack channels.
   - Share individual stories and 5-article digests to Slack or WhatsApp with one click.

---

## 🌐 Live Access

Open the dashboard on your phone, tablet, or computer:

👉 **[https://chinmayram.github.io/pulsenews/](https://chinmayram.github.io/pulsenews/)**

- **Mobile Ready**: Optimized responsive layout for iPhone, Android, iPad, and desktop.
- **Instant Filtering**: <5ms client-side search and multi-dimensional filter switching.
- **Auto-Refreshed**: Scraped every 2 hours with 800+ fresh headlines across all 5 sources.

---

## 💻 Running Locally (Optional)

If you wish to run the live Python FastAPI backend locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python main.py
```

Local development dashboard runs at http://localhost:8080.
