# PulseNews: Multi-Source News Aggregator & Live Dashboard

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

## 🚀 Deployment to GitHub Pages (Access from Mobile)

Deploying to GitHub Pages allows you to open PulseNews directly from your phone without firewall or local Wi-Fi restrictions!

### Step 1: Create a GitHub Repository
1. Go to [github.com/new](https://github.com/new).
2. Name your repository (e.g. pulsenews).
3. Set visibility to **Public** and leave  Add a README unchecked.
4. Click **Create repository**.

### Step 2: Push the Code
In this project folder, run:
`ash
git remote add origin https://github.com/<YOUR_USERNAME>/pulsenews.git
git branch -M main
git push -u origin main
`

### Step 3: Enable GitHub Pages
1. On your GitHub repository page, go to **Settings** > **Pages**.
2. Under **Build and deployment > Source**, select **GitHub Actions**.
3. Go to the **Actions** tab to watch the automated deployment run.
4. Once completed, your live URL will be ready:
   👉 **https://<YOUR_USERNAME>.github.io/pulsenews/**

Open that link on your iPhone, Android, tablet, or laptop — it works anywhere!

---

## 💻 Running Locally (FastAPI)

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)

`ash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python main.py
`
Open **[http://localhost:8080](http://localhost:8080)** in your browser.
