// PulseNews Frontend Engine - 3-Tier Interactive Filter Architecture
document.addEventListener('DOMContentLoaded', () => {
    // App State
    const state = {
        currentLocation: 'all',
        currentTopic: 'priority',
        currentSource: 'all',
        searchQuery: '',
        locations: {},
        topics: {},
        sources: {},
        priorityOrder: [],
        enabledTopics: {},
        filterCounts: { locations: {}, topics: {}, sources: {} },
        articles: [],
        lastRefreshed: 0,
        isRefreshing: false,
        theme: localStorage.getItem('pulse_theme') || 'dark'
    };

    // Dual-Mode Deployment Architecture: Detect GitHub Pages / Static Hosting
    let isStaticMode = window.location.hostname.endsWith('github.io') || window.location.protocol === 'file:';
    let staticMasterArticles = null;

    // DOM Elements
    const elements = {
        articlesGrid: document.getElementById('articlesGrid'),
        loadingState: document.getElementById('loadingState'),
        emptyState: document.getElementById('emptyState'),
        emptyStateDetail: document.getElementById('emptyStateDetail'),
        resetFiltersEmptyBtn: document.getElementById('resetFiltersEmptyBtn'),
        clearAllFiltersBtn: document.getElementById('clearAllFiltersBtn'),
        activeFilterBreadcrumb: document.getElementById('activeFilterBreadcrumb'),
        articleCountBadge: document.getElementById('articleCountBadge'),
        refreshBtn: document.getElementById('refreshBtn'),
        refreshBtnMobile: document.getElementById('refreshBtnMobile'),
        refreshIcon: document.getElementById('refreshIcon'),
        refreshBtnText: document.getElementById('refreshBtnText'),
        lastRefreshedTime: document.getElementById('lastRefreshedTime'),
        headerStatus: document.getElementById('headerStatus'),
        searchInput: document.getElementById('searchInput'),
        clearSearchBtn: document.getElementById('clearSearchBtn'),
        openPriorityBtn: document.getElementById('openPriorityBtn'),
        openPriorityBtnMobile: document.getElementById('openPriorityBtnMobile'),
        editTopicPriorityBtn: document.getElementById('editTopicPriorityBtn'),
        priorityModal: document.getElementById('priorityModal'),
        closePriorityModalBtn: document.getElementById('closePriorityModalBtn'),
        cancelPriorityBtn: document.getElementById('cancelPriorityBtn'),
        savePriorityBtn: document.getElementById('savePriorityBtn'),
        resetPriorityBtn: document.getElementById('resetPriorityBtn'),
        modalPriorityList: document.getElementById('modalPriorityList'),
        xTokenInput: document.getElementById('xTokenInput'),
        toastNotification: document.getElementById('toastNotification'),
        toastMessage: document.getElementById('toastMessage'),
        themeToggleBtn: document.getElementById('themeToggleBtn'),
        themeIcon: document.getElementById('themeIcon'),
        // Slack Elements
        sendSlackDashboardBtn: document.getElementById('sendSlackDashboardBtn'),
        openSlackModalBtn: document.getElementById('openSlackModalBtn'),
        slackModal: document.getElementById('slackModal'),
        closeSlackModalBtn: document.getElementById('closeSlackModalBtn'),
        cancelSlackBtn: document.getElementById('cancelSlackBtn'),
        saveSlackBtn: document.getElementById('saveSlackBtn'),
        testSlackBtn: document.getElementById('testSlackBtn'),
        testSlackBtnText: document.getElementById('testSlackBtnText'),
        sendDashboardNowBtn: document.getElementById('sendDashboardNowBtn'),
        sendDigestNowBtn: document.getElementById('sendDigestNowBtn'),
        slackWebhookInput: document.getElementById('slackWebhookInput'),
        slackChannelInput: document.getElementById('slackChannelInput'),
        slackBotNameInput: document.getElementById('slackBotNameInput'),
        slackStatusBadge: document.getElementById('slackStatusBadge')
    };

    const LOCATION_META = {
        all: { name: 'All Locations', icon: 'globe' },
        bengaluru: { name: 'Bengaluru', icon: 'building-2' },
        odisha: { name: 'Odisha', icon: 'landmark' },
        india: { name: 'India', icon: 'flag' },
        global: { name: 'Global', icon: 'globe-2' }
    };

    const TOPIC_META = {
        priority: { name: 'Priority Feed', icon: 'flame' },
        job_market: { name: 'Job Market', icon: 'briefcase' },
        technology: { name: 'Technology', icon: 'cpu' },
        entertainment: { name: 'Entertainment', icon: 'film' },
        general: { name: 'General News', icon: 'newspaper' }
    };

    const SOURCE_META = {
        all: { name: 'All Sources' },
        google: { name: 'Google News', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
        msn: { name: 'MSN News', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
        yahoo: { name: 'Yahoo News', bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30' },
        x: { name: 'X (Twitter)', bg: 'bg-sky-500/15 text-sky-300 border-sky-500/30' },
        moneycontrol: { name: 'Moneycontrol', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30' }
    };

    // Initialize Theme
    function initTheme() {
        if (state.theme === 'light') {
            document.documentElement.classList.remove('dark');
            document.documentElement.classList.add('light');
            if (elements.themeIcon) elements.themeIcon.setAttribute('data-lucide', 'moon');
        } else {
            document.documentElement.classList.remove('light');
            document.documentElement.classList.add('dark');
            if (elements.themeIcon) elements.themeIcon.setAttribute('data-lucide', 'sun');
        }
        if (window.lucide) lucide.createIcons();
    }

    elements.themeToggleBtn.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('pulse_theme', state.theme);
        initTheme();
    });

    function timeAgo(epochSeconds) {
        if (!epochSeconds) return 'Recently';
        const diff = Math.max(0, Math.floor(Date.now() / 1000 - epochSeconds));
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    function showToast(message) {
        elements.toastMessage.textContent = message;
        elements.toastNotification.classList.remove('hidden');
        setTimeout(() => {
            elements.toastNotification.classList.add('hidden');
        }, 3500);
    }

    // Load Config (Priority, Locations, Topics) - Dual Mode
    async function loadConfig() {
        if (!isStaticMode) {
            try {
                const res = await fetch('/api/config');
                if (res.ok) {
                    const data = await res.json();
                    state.locations = data.locations || {};
                    state.topics = data.topics || {};
                    state.sources = data.sources || {};
                    state.priorityOrder = data.priority_order || [];
                    state.enabledTopics = data.enabled_topics || {};
                    return;
                }
            } catch (err) {
                console.warn('FastAPI backend not reachable, falling back to static mode:', err);
                isStaticMode = true;
            }
        }

        // Static Mode Fallback: load ./data/config.json
        try {
            const res = await fetch('./data/config.json');
            if (!res.ok) throw new Error('Failed to load ./data/config.json');
            const data = await res.json();
            state.locations = data.locations || {};
            state.topics = data.topics || {};
            state.sources = data.sources || {};

            const savedPriority = localStorage.getItem('pulse_priority_order');
            const savedEnabled = localStorage.getItem('pulse_enabled_topics');
            state.priorityOrder = savedPriority ? JSON.parse(savedPriority) : (data.priority_order || ['job_market', 'technology', 'entertainment', 'general']);
            state.enabledTopics = savedEnabled ? JSON.parse(savedEnabled) : (data.enabled_topics || {});
        } catch (err) {
            console.error('Error loading static config:', err);
        }
    }

    // Update Interactive Filter Counts in UI
    function updateInteractiveCounts(filterCounts) {
        if (!filterCounts) return;
        state.filterCounts = filterCounts;

        // 1. Update Location Counts
        const locCounts = filterCounts.locations || {};
        Object.keys(LOCATION_META).forEach(locKey => {
            const span = document.getElementById(`count-loc-${locKey}`);
            if (span) {
                span.textContent = locCounts[locKey] ?? 0;
            }
        });

        // 2. Update Topic Counts
        const topCounts = filterCounts.topics || {};
        Object.keys(TOPIC_META).forEach(topKey => {
            const span = document.getElementById(`count-top-${topKey}`);
            if (span) {
                span.textContent = topCounts[topKey] ?? 0;
            }
        });

        // 3. Update Source Counts
        const srcCounts = filterCounts.sources || {};
        Object.keys(SOURCE_META).forEach(srcKey => {
            const span = document.getElementById(`count-src-${srcKey}`);
            if (span) {
                span.textContent = `(${srcCounts[srcKey] ?? 0})`;
            }
        });
    }

    // Update Breadcrumb Status
    function updateBreadcrumbStatus(totalCount) {
        const locName = LOCATION_META[state.currentLocation]?.name || state.currentLocation;
        const topName = TOPIC_META[state.currentTopic]?.name || state.currentTopic;
        const srcName = SOURCE_META[state.currentSource]?.name || state.currentSource;

        let html = `
            <span class="inline-flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                <i data-lucide="map-pin" class="w-3 h-3"></i> ${locName}
            </span>
            <span class="text-slate-500">&rsaquo;</span>
            <span class="inline-flex items-center gap-1 text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded-md border border-indigo-500/20">
                <i data-lucide="tag" class="w-3 h-3"></i> ${topName}
            </span>
        `;

        if (state.currentSource !== 'all') {
            html += `
                <span class="text-slate-500">&rsaquo;</span>
                <span class="inline-flex items-center gap-1 text-slate-300 bg-slate-800 px-2 py-0.5 rounded-md border border-slate-700">
                    <i data-lucide="filter" class="w-3 h-3"></i> ${srcName}
                </span>
            `;
        }

        if (state.searchQuery) {
            html += `
                <span class="text-slate-500">&rsaquo;</span>
                <span class="text-indigo-400 font-medium">"${state.searchQuery}"</span>
            `;
        }

        elements.activeFilterBreadcrumb.innerHTML = html;
        elements.articleCountBadge.textContent = `${totalCount} stories`;

        // Show/hide Clear All button
        const isNonDefault = state.currentLocation !== 'all' || state.currentTopic !== 'priority' || state.currentSource !== 'all' || state.searchQuery !== '';
        if (isNonDefault) {
            elements.clearAllFiltersBtn.classList.remove('hidden');
        } else {
            elements.clearAllFiltersBtn.classList.add('hidden');
        }

        if (window.lucide) lucide.createIcons();
    }

    // Fetch News Articles (Dual-Mode: Live API or Client-Side Static Engine)
    async function fetchNews() {
        showLoading(true);
        try {
            if (!isStaticMode) {
                const params = new URLSearchParams({
                    location: state.currentLocation,
                    topic: state.currentTopic,
                    source: state.currentSource,
                    limit: '150'
                });
                if (state.searchQuery) {
                    params.append('search', state.searchQuery);
                }

                const res = await fetch(`/api/news?${params.toString()}`);
                if (res.ok) {
                    const data = await res.json();
                    state.lastRefreshed = data.last_refreshed;
                    updateLastRefreshedDisplay();
                    state.articles = data.articles || [];
                    updateInteractiveCounts(data.filter_counts);
                    renderArticles(state.articles);
                    updateBreadcrumbStatus(data.count);
                    return;
                } else {
                    console.warn('/api/news failed, falling back to static mode');
                    isStaticMode = true;
                }
            }

            // Static Mode Execution
            await fetchNewsStatic();
        } catch (err) {
            console.warn('API error, falling back to static mode:', err);
            isStaticMode = true;
            try {
                await fetchNewsStatic();
            } catch (staticErr) {
                console.error('Static fetch error:', staticErr);
                showToast('Error loading news feed. Please try refreshing.');
            }
        } finally {
            showLoading(false);
        }
    }

    // Static Client-Side News Filtering Engine
    async function fetchNewsStatic() {
        if (!staticMasterArticles) {
            const res = await fetch(`./data/news.json?_t=${Date.now()}`);
            if (!res.ok) throw new Error(`Failed to load ./data/news.json (HTTP ${res.status})`);
            const data = await res.json();
            staticMasterArticles = data.articles || [];
            state.lastRefreshed = data.last_refreshed || Math.floor(Date.now() / 1000);
            updateLastRefreshedDisplay();
        }

        const filtered = filterArticlesStatic(
            staticMasterArticles,
            state.currentLocation,
            state.currentTopic,
            state.currentSource,
            state.searchQuery,
            state.priorityOrder,
            state.enabledTopics
        );

        const counts = getFilterCountsStatic(
            staticMasterArticles,
            state.currentLocation,
            state.currentTopic,
            state.currentSource,
            state.searchQuery
        );

        state.articles = filtered.slice(0, 150);
        updateInteractiveCounts(counts);
        renderArticles(state.articles);
        updateBreadcrumbStatus(state.articles.length);
    }

    function filterArticlesStatic(articles, location, topic, source, searchQuery, priorityOrder, enabledTopics) {
        let filtered = [...articles];

        // 1. Location filter
        if (location && location !== 'all') {
            filtered = filtered.filter(a => (a.location || '').toLowerCase() === location.toLowerCase());
        }

        // 2. Source filter
        if (source && source !== 'all') {
            filtered = filtered.filter(a => (a.source || '').toLowerCase() === source.toLowerCase());
        }

        // 3. Search query
        if (searchQuery && searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase();
            filtered = filtered.filter(a =>
                (a.title || '').toLowerCase().includes(q) ||
                (a.summary || '').toLowerCase().includes(q) ||
                (a.source_name || '').toLowerCase().includes(q) ||
                (a.location_name || '').toLowerCase().includes(q) ||
                (a.topic_name || '').toLowerCase().includes(q)
            );
        }

        // 4. Topic filter / Priority interleaving
        if (topic && topic !== 'all' && topic !== 'priority') {
            filtered = filtered.filter(a => (a.topic || '').toLowerCase() === topic.toLowerCase());
        } else {
            const activeTopics = (priorityOrder && priorityOrder.length > 0)
                ? priorityOrder.filter(t => t !== 'priority' && (!enabledTopics || enabledTopics[t] !== false))
                : ['job_market', 'technology', 'entertainment', 'general'];

            ['job_market', 'technology', 'entertainment', 'general'].forEach(dt => {
                if (!activeTopics.includes(dt) && (!enabledTopics || enabledTopics[dt] !== false)) {
                    activeTopics.push(dt);
                }
            });

            const topicBuckets = {};
            activeTopics.forEach(t => { topicBuckets[t] = []; });
            const leftover = [];

            filtered.forEach(a => {
                const top = (a.topic || '').toLowerCase();
                if (topicBuckets[top]) {
                    topicBuckets[top].push(a);
                } else {
                    leftover.push(a);
                }
            });

            const getQuota = (idx) => {
                if (idx === 0) return 4;
                if (idx <= 2) return 3;
                return 2;
            };

            const interleaved = [];
            let hasMore = true;
            while (hasMore) {
                hasMore = false;
                for (let idx = 0; idx < activeTopics.length; idx++) {
                    const t = activeTopics[idx];
                    const quota = getQuota(idx);
                    const bucket = topicBuckets[t];
                    for (let q = 0; q < quota; q++) {
                        if (bucket && bucket.length > 0) {
                            interleaved.push(bucket.shift());
                            hasMore = true;
                        }
                    }
                }
            }
            interleaved.push(...leftover);

            // Deduplicate
            const seen = new Set();
            filtered = [];
            for (const a of interleaved) {
                const key = a.id || (a.title ? a.title.toLowerCase().slice(0, 60) : Math.random());
                if (!seen.has(key)) {
                    seen.add(key);
                    filtered.push(a);
                }
            }
        }

        return filtered;
    }

    function getFilterCountsStatic(articles, activeLoc, activeTop, activeSrc, searchQuery) {
        let base = [...articles];
        if (searchQuery && searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase();
            base = base.filter(a =>
                (a.title || '').toLowerCase().includes(q) ||
                (a.summary || '').toLowerCase().includes(q) ||
                (a.source_name || '').toLowerCase().includes(q)
            );
        }

        // 1. Location counts (conditioned on active source and active topic)
        let locBase = base;
        if (activeSrc && activeSrc !== 'all') {
            locBase = locBase.filter(a => (a.source || '').toLowerCase() === activeSrc.toLowerCase());
        }
        if (activeTop && activeTop !== 'all' && activeTop !== 'priority') {
            locBase = locBase.filter(a => (a.topic || '').toLowerCase() === activeTop.toLowerCase());
        }
        const locationCounts = { all: locBase.length };
        ['bengaluru', 'odisha', 'india', 'global'].forEach(locId => {
            locationCounts[locId] = locBase.filter(a => (a.location || '').toLowerCase() === locId).length;
        });

        // 2. Topic counts (conditioned on active location and active source)
        let topBase = base;
        if (activeLoc && activeLoc !== 'all') {
            topBase = topBase.filter(a => (a.location || '').toLowerCase() === activeLoc.toLowerCase());
        }
        if (activeSrc && activeSrc !== 'all') {
            topBase = topBase.filter(a => (a.source || '').toLowerCase() === activeSrc.toLowerCase());
        }
        const topicCounts = { all: topBase.length, priority: topBase.length };
        ['job_market', 'technology', 'entertainment', 'general'].forEach(topId => {
            topicCounts[topId] = topBase.filter(a => (a.topic || '').toLowerCase() === topId).length;
        });

        // 3. Source counts (conditioned on active location and active topic)
        let srcBase = base;
        if (activeLoc && activeLoc !== 'all') {
            srcBase = srcBase.filter(a => (a.location || '').toLowerCase() === activeLoc.toLowerCase());
        }
        if (activeTop && activeTop !== 'all' && activeTop !== 'priority') {
            srcBase = srcBase.filter(a => (a.topic || '').toLowerCase() === activeTop.toLowerCase());
        }
        const sourceCounts = { all: srcBase.length, google: 0, msn: 0, yahoo: 0, x: 0, moneycontrol: 0 };
        srcBase.forEach(a => {
            const s = (a.source || '').toLowerCase();
            if (s in sourceCounts) {
                sourceCounts[s]++;
            }
        });

        return {
            locations: locationCounts,
            topics: topicCounts,
            sources: sourceCounts
        };
    }

    // Refresh Action (Dual-Mode: Scrapes Live via API or Reloads from Static JSON)
    async function handleRefresh() {
        if (state.isRefreshing) return;
        state.isRefreshing = true;
        setRefreshingUI(true);

        if (isStaticMode) {
            try {
                const res = await fetch(`./data/news.json?_t=${Date.now()}`);
                if (!res.ok) throw new Error('Failed to reload ./data/news.json');
                const data = await res.json();
                staticMasterArticles = data.articles || [];
                state.lastRefreshed = data.last_refreshed || Math.floor(Date.now() / 1000);
                await fetchNewsStatic();
                showToast('News feed reloaded! (Auto-updated every 2h by GitHub Actions)');
            } catch (err) {
                console.error('Static refresh error:', err);
                showToast('Could not reload feed.');
            } finally {
                state.isRefreshing = false;
                setRefreshingUI(false);
            }
            return;
        }

        try {
            const res = await fetch('/api/news/refresh', { method: 'POST' });
            if (!res.ok) throw new Error('Refresh request failed');
            const data = await res.json();

            showToast(data.message || 'News refreshed from all 5 sources!');
            await loadConfig();
            await fetchNews();
        } catch (err) {
            console.error('Error refreshing news:', err);
            showToast('Refresh failed. Please check internet connection.');
        } finally {
            state.isRefreshing = false;
            setRefreshingUI(false);
        }
    }

    function setRefreshingUI(isRefreshing) {
        if (isRefreshing) {
            elements.refreshIcon.classList.add('spinning');
            elements.refreshBtnText.textContent = 'Scraping Sources...';
            elements.headerStatus.textContent = 'Scraping Google, MSN, Yahoo, X & Moneycontrol in parallel...';
            elements.refreshBtn.disabled = true;
        } else {
            elements.refreshIcon.classList.remove('spinning');
            elements.refreshBtnText.textContent = 'Refresh News';
            elements.headerStatus.textContent = 'Google News • MSN • Yahoo • Verified X • Moneycontrol';
            elements.refreshBtn.disabled = false;
        }
    }

    function showLoading(show) {
        if (show) {
            elements.loadingState.classList.remove('hidden');
            elements.articlesGrid.classList.add('hidden');
            elements.emptyState.classList.add('hidden');
        } else {
            elements.loadingState.classList.add('hidden');
            elements.articlesGrid.classList.remove('hidden');
        }
    }

    function updateLastRefreshedDisplay() {
        if (elements.lastRefreshedTime) {
            elements.lastRefreshedTime.textContent = timeAgo(state.lastRefreshed);
        }
    }

    // Render News Cards
    function renderArticles(articles) {
        elements.articlesGrid.innerHTML = '';

        if (!articles || articles.length === 0) {
            elements.articlesGrid.classList.add('hidden');
            elements.emptyState.classList.remove('hidden');

            const locName = LOCATION_META[state.currentLocation]?.name || state.currentLocation;
            const topName = TOPIC_META[state.currentTopic]?.name || state.currentTopic;
            const srcName = SOURCE_META[state.currentSource]?.name || state.currentSource;

            elements.emptyStateDetail.textContent = `No stories found for ${locName} under "${topName}" from ${srcName}. Try expanding your filters.`;
            return;
        }

        elements.emptyState.classList.add('hidden');
        elements.articlesGrid.classList.remove('hidden');

        articles.forEach(article => {
            const card = document.createElement('article');
            card.className = 'news-card glass-panel rounded-2xl p-4 border border-slate-800/80 flex flex-col justify-between group relative overflow-hidden';

            const sourceMeta = SOURCE_META[article.source] || { name: article.source_name, bg: 'bg-slate-800 text-slate-300' };

            const title = escapeHtml(article.title);
            const summary = escapeHtml(article.summary);
            const author = escapeHtml(article.author || article.source_name);
            const relTime = article.published_relative || timeAgo(article.timestamp);
            const imageUrl = article.image_url || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&auto=format&fit=crop&q=80';

            const isXSource = article.source === 'x';
            const actionText = isXSource ? 'View Post' : 'Read Story';
            const actionIcon = isXSource ? 'twitter' : 'external-link';

            card.innerHTML = `
                <div>
                    <!-- Article Featured Image Banner -->
                    <div class="relative w-full h-44 rounded-xl overflow-hidden mb-3.5 bg-slate-900 border border-slate-800/60 shadow-inner">
                        <img
                            src="${imageUrl}"
                            alt="${title}"
                            loading="lazy"
                            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
                            onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&auto=format&fit=crop&q=80';"
                        />
                        <!-- Gradient Overlay -->
                        <div class="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-950/20 to-black/40"></div>

                        <!-- Top Floating Source Badge -->
                        <div class="absolute top-2.5 left-2.5">
                            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-bold border backdrop-blur-md ${sourceMeta.bg}">
                                ${isXSource ? '<span class="text-xs">𝕏</span>' : ''}
                                ${sourceMeta.name}
                            </span>
                        </div>

                        <!-- Bottom Floating Tags -->
                        <div class="absolute bottom-2.5 left-2.5 flex items-center gap-1.5 flex-wrap">
                            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-black/70 text-amber-300 border border-amber-500/30 backdrop-blur-md">
                                <i data-lucide="map-pin" class="w-2.5 h-2.5"></i>
                                ${article.location_name}
                            </span>
                            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-black/70 text-indigo-300 border border-indigo-500/30 backdrop-blur-md">
                                ${article.topic_name}
                            </span>
                        </div>

                        <!-- Published Relative Time -->
                        <span class="absolute bottom-2.5 right-2.5 text-[10px] text-slate-300 font-medium px-2 py-0.5 rounded-md bg-black/70 border border-white/10 backdrop-blur-md">
                            ${relTime}
                        </span>
                    </div>

                    <!-- Article Headline -->
                    <h3 class="text-sm md:text-base font-bold text-slate-100 group-hover:text-indigo-400 transition leading-snug mb-2 line-clamp-2">
                        <a href="${article.link}" target="_blank" rel="noopener noreferrer">
                            ${title}
                        </a>
                    </h3>

                    <!-- Article Snippet -->
                    <p class="text-xs text-slate-400 leading-relaxed line-clamp-3 mb-4">
                        ${summary}
                    </p>
                </div>

                <!-- Card Footer Actions -->
                <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs mt-auto gap-2">
                    <span class="text-[11px] text-slate-400 truncate max-w-[120px] md:max-w-[140px]" title="${author}">
                        ${author}
                    </span>
                    <div class="flex items-center gap-1.5">
                        <button
                            type="button"
                            class="slack-share-card-btn inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-[#4A154B]/30 hover:bg-[#4A154B]/60 text-purple-200 border border-purple-500/30 transition text-[11px] font-semibold active:scale-95"
                            title="Send story to Slack channel"
                        >
                            <i data-lucide="hash" class="w-3.5 h-3.5 text-[#36C5F0]"></i>
                            <span class="hidden sm:inline">Slack</span>
                        </button>
                        <a
                            href="${article.link}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center gap-1.5 font-semibold text-indigo-400 hover:text-indigo-300 transition group-hover:translate-x-0.5"
                        >
                            <span>${actionText}</span>
                            <i data-lucide="${actionIcon}" class="w-3.5 h-3.5"></i>
                        </a>
                    </div>
                </div>
            `;

            const slackCardBtn = card.querySelector('.slack-share-card-btn');
            if (slackCardBtn) {
                slackCardBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    sendArticleToSlack(article, slackCardBtn);
                });
            }

            elements.articlesGrid.appendChild(card);
        });

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 1. Location Pill Event Listeners
    document.querySelectorAll('.location-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.location-pill').forEach(p => {
                p.classList.remove('active', 'bg-amber-500', 'text-slate-950', 'shadow-md', 'font-bold');
                p.classList.add('bg-slate-800/80', 'text-slate-200', 'font-medium');
                const badge = p.querySelector('span:last-child');
                if (badge) badge.className = 'px-1.5 py-0.2 rounded-full text-[10px] bg-slate-900 text-slate-300';
            });

            pill.classList.add('active', 'bg-amber-500', 'text-slate-950', 'shadow-md', 'font-bold');
            pill.classList.remove('bg-slate-800/80', 'text-slate-200', 'font-medium');
            const activeBadge = pill.querySelector('span:last-child');
            if (activeBadge) activeBadge.className = 'px-1.5 py-0.2 rounded-full text-[10px] bg-black/20 font-bold';

            state.currentLocation = pill.getAttribute('data-location');
            fetchNews();
        });
    });

    // 2. Topic Pill Event Listeners
    document.querySelectorAll('.topic-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.topic-pill').forEach(p => {
                p.classList.remove('active', 'bg-gradient-to-r', 'from-indigo-600', 'to-purple-600', 'text-white', 'shadow-md', 'font-bold');
                p.classList.add('bg-slate-800/80', 'text-slate-200', 'font-medium');
                const badge = p.querySelector('span:last-child');
                if (badge) badge.className = 'px-1.5 py-0.2 rounded-full text-[10px] bg-slate-900 text-slate-300';
            });

            pill.classList.add('active', 'bg-gradient-to-r', 'from-indigo-600', 'to-purple-600', 'text-white', 'shadow-md', 'font-bold');
            pill.classList.remove('bg-slate-800/80', 'text-slate-200', 'font-medium');
            const activeBadge = pill.querySelector('span:last-child');
            if (activeBadge) activeBadge.className = 'px-1.5 py-0.2 rounded-full text-[10px] bg-black/30 font-bold';

            state.currentTopic = pill.getAttribute('data-topic');
            fetchNews();
        });
    });

    // 3. Source Chip Event Listeners
    document.querySelectorAll('.source-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.source-chip').forEach(c => {
                c.classList.remove('active', 'bg-indigo-600', 'text-white', 'font-bold');
                c.classList.add('bg-slate-900/80', 'text-slate-300', 'font-medium');
            });

            chip.classList.add('active', 'bg-indigo-600', 'text-white', 'font-bold');
            chip.classList.remove('bg-slate-900/80', 'text-slate-300', 'font-medium');

            state.currentSource = chip.getAttribute('data-source');
            fetchNews();
        });
    });

    // Reset All Filters Helper
    function resetAllFilters() {
        // Reset Location to "all"
        document.querySelectorAll('.location-pill').forEach(p => {
            p.classList.remove('active', 'bg-amber-500', 'text-slate-950', 'shadow-md', 'font-bold');
            p.classList.add('bg-slate-800/80', 'text-slate-200', 'font-medium');
        });
        const allLoc = document.querySelector('.location-pill[data-location="all"]');
        if (allLoc) {
            allLoc.classList.add('active', 'bg-amber-500', 'text-slate-950', 'shadow-md', 'font-bold');
            allLoc.classList.remove('bg-slate-800/80', 'text-slate-200');
        }
        state.currentLocation = 'all';

        // Reset Topic to "priority"
        document.querySelectorAll('.topic-pill').forEach(p => {
            p.classList.remove('active', 'bg-gradient-to-r', 'from-indigo-600', 'to-purple-600', 'text-white', 'shadow-md', 'font-bold');
            p.classList.add('bg-slate-800/80', 'text-slate-200', 'font-medium');
        });
        const priorityTop = document.querySelector('.topic-pill[data-topic="priority"]');
        if (priorityTop) {
            priorityTop.classList.add('active', 'bg-gradient-to-r', 'from-indigo-600', 'to-purple-600', 'text-white', 'shadow-md', 'font-bold');
            priorityTop.classList.remove('bg-slate-800/80', 'text-slate-200');
        }
        state.currentTopic = 'priority';

        // Reset Source to "all"
        document.querySelectorAll('.source-chip').forEach(c => {
            c.classList.remove('active', 'bg-indigo-600', 'text-white', 'font-bold');
            c.classList.add('bg-slate-900/80', 'text-slate-300', 'font-medium');
        });
        const allSrc = document.querySelector('.source-chip[data-source="all"]');
        if (allSrc) {
            allSrc.classList.add('active', 'bg-indigo-600', 'text-white', 'font-bold');
            allSrc.classList.remove('bg-slate-900/80', 'text-slate-300');
        }
        state.currentSource = 'all';

        // Clear Search
        elements.searchInput.value = '';
        state.searchQuery = '';
        elements.clearSearchBtn.classList.add('hidden');

        fetchNews();
    }

    if (elements.resetFiltersEmptyBtn) elements.resetFiltersEmptyBtn.addEventListener('click', resetAllFilters);
    if (elements.clearAllFiltersBtn) elements.clearAllFiltersBtn.addEventListener('click', resetAllFilters);

    // Search Input Handling with Debounce
    let searchDebounceTimer;
    elements.searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounceTimer);
        const val = e.target.value.trim();
        state.searchQuery = val;

        if (val.length > 0) {
            elements.clearSearchBtn.classList.remove('hidden');
        } else {
            elements.clearSearchBtn.classList.add('hidden');
        }

        searchDebounceTimer = setTimeout(() => {
            fetchNews();
        }, 300);
    });

    elements.clearSearchBtn.addEventListener('click', () => {
        elements.searchInput.value = '';
        state.searchQuery = '';
        elements.clearSearchBtn.classList.add('hidden');
        fetchNews();
    });

    elements.refreshBtn.addEventListener('click', handleRefresh);
    if (elements.refreshBtnMobile) {
        elements.refreshBtnMobile.addEventListener('click', handleRefresh);
    }

    // Priority Customizer Modal
    let localPriorityOrder = [];
    function openPriorityModal() {
        localPriorityOrder = [...state.priorityOrder];
        renderModalPriorityList();
        elements.priorityModal.classList.remove('hidden');
        elements.priorityModal.classList.add('flex');
    }

    function closePriorityModal() {
        elements.priorityModal.classList.add('hidden');
        elements.priorityModal.classList.remove('flex');
    }

    elements.openPriorityBtn.addEventListener('click', openPriorityModal);
    if (elements.openPriorityBtnMobile) elements.openPriorityBtnMobile.addEventListener('click', openPriorityModal);
    if (elements.editTopicPriorityBtn) elements.editTopicPriorityBtn.addEventListener('click', openPriorityModal);

    elements.closePriorityModalBtn.addEventListener('click', closePriorityModal);
    elements.cancelPriorityBtn.addEventListener('click', closePriorityModal);

    function renderModalPriorityList() {
        elements.modalPriorityList.innerHTML = '';

        localPriorityOrder.forEach((topId, index) => {
            const top = state.topics[topId] || TOPIC_META[topId] || { name: topId, description: '' };

            const item = document.createElement('div');
            item.className = 'priority-item flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 select-none';
            item.setAttribute('draggable', 'true');
            item.dataset.index = index;

            item.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-400 font-bold text-xs flex items-center justify-center border border-indigo-500/20">
                        ${index + 1}
                    </div>
                    <div>
                        <div class="text-xs font-bold text-slate-200 flex items-center gap-2">
                            <span>${top.name}</span>
                            ${index === 0 ? '<span class="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30">Top Priority</span>' : ''}
                        </div>
                        <p class="text-[11px] text-slate-400 leading-tight">${top.description || ''}</p>
                    </div>
                </div>

                <div class="flex items-center gap-1.5">
                    <button class="btn-move-up p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition ${index === 0 ? 'opacity-30 cursor-not-allowed' : ''}" data-index="${index}">
                        <i data-lucide="chevron-up" class="w-4 h-4"></i>
                    </button>
                    <button class="btn-move-down p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition ${index === localPriorityOrder.length - 1 ? 'opacity-30 cursor-not-allowed' : ''}" data-index="${index}">
                        <i data-lucide="chevron-down" class="w-4 h-4"></i>
                    </button>
                </div>
            `;

            item.querySelector('.btn-move-up')?.addEventListener('click', (e) => {
                e.stopPropagation();
                if (index > 0) {
                    const temp = localPriorityOrder[index];
                    localPriorityOrder[index] = localPriorityOrder[index - 1];
                    localPriorityOrder[index - 1] = temp;
                    renderModalPriorityList();
                }
            });

            item.querySelector('.btn-move-down')?.addEventListener('click', (e) => {
                e.stopPropagation();
                if (index < localPriorityOrder.length - 1) {
                    const temp = localPriorityOrder[index];
                    localPriorityOrder[index] = localPriorityOrder[index + 1];
                    localPriorityOrder[index + 1] = temp;
                    renderModalPriorityList();
                }
            });

            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', index);
                item.classList.add('dragging');
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });

            item.addEventListener('dragover', (e) => {
                e.preventDefault();
            });

            item.addEventListener('drop', (e) => {
                e.preventDefault();
                const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
                const toIndex = index;
                if (!isNaN(fromIndex) && fromIndex !== toIndex) {
                    const movedItem = localPriorityOrder.splice(fromIndex, 1)[0];
                    localPriorityOrder.splice(toIndex, 0, movedItem);
                    renderModalPriorityList();
                }
            });

            elements.modalPriorityList.appendChild(item);
        });

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    elements.savePriorityBtn.addEventListener('click', async () => {
        if (isStaticMode) {
            state.priorityOrder = [...localPriorityOrder];
            localStorage.setItem('pulse_priority_order', JSON.stringify(localPriorityOrder));
            closePriorityModal();
            showToast('Priority settings saved to browser!');
            fetchNews();
            return;
        }

        try {
            const payload = {
                priority_order: localPriorityOrder
            };
            const token = elements.xTokenInput.value.trim();
            if (token) {
                payload.x_bearer_token = token;
            }

            const res = await fetch('/api/priority', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Failed to save priority settings');
            const data = await res.json();

            state.priorityOrder = data.settings.priority_order;
            closePriorityModal();
            showToast('Priority settings saved! Feed updated.');
            fetchNews();
        } catch (err) {
            console.error('Error saving priority:', err);
            showToast('Failed to save priority settings.');
        }
    });

    elements.resetPriorityBtn.addEventListener('click', () => {
        localPriorityOrder = ['job_market', 'technology', 'entertainment', 'general'];
        renderModalPriorityList();
    });

    // Force clear search input on startup and suppress lingering browser credential autofill
    if (elements.searchInput) {
        elements.searchInput.value = '';
        state.searchQuery = '';
        setTimeout(() => {
            if (elements.searchInput.value.toLowerCase() === 'admin') {
                elements.searchInput.value = '';
                state.searchQuery = '';
                if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');
                fetchNews();
            }
        }, 150);
        setTimeout(() => {
            if (elements.searchInput.value.toLowerCase() === 'admin') {
                elements.searchInput.value = '';
                state.searchQuery = '';
                if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');
            }
        }, 600);
    }

    // ==========================================
    // Slack Integration & Dispatch Engine
    // ==========================================

    // Send Single Article to Slack Channel
    async function sendArticleToSlack(article, btnElement) {
        if (!article) return;

        const originalHtml = btnElement ? btnElement.innerHTML : null;
        if (btnElement) {
            btnElement.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-[#36C5F0]"></i><span class="hidden sm:inline">Sending</span>`;
            btnElement.disabled = true;
            if (window.lucide) lucide.createIcons();
        }

        try {
            const payload = {
                title: article.title,
                link: article.link,
                summary: article.summary || '',
                source: article.source || 'news',
                source_name: article.source_name || (SOURCE_META[article.source]?.name) || 'News',
                location: article.location || 'all',
                location_name: article.location_name || (LOCATION_META[article.location]?.name) || 'All',
                topic: article.topic || 'general',
                topic_name: article.topic_name || (TOPIC_META[article.topic]?.name) || 'General',
                image_url: article.image_url || null
            };

            const res = await fetch('/api/slack/send_article', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) {
                if (data.detail && data.detail.includes('Slack Webhook URL is not configured')) {
                    showToast('Please configure your Slack Webhook URL first.');
                    openSlackModal();
                    return;
                }
                throw new Error(data.detail || 'Failed to dispatch article to Slack');
            }

            showToast(data.message || 'Story sent to Slack!');
        } catch (err) {
            console.error('Slack story dispatch error:', err);
            showToast(`Slack Error: ${err.message}`);
        } finally {
            if (btnElement && originalHtml) {
                btnElement.innerHTML = originalHtml;
                btnElement.disabled = false;
                if (window.lucide) lucide.createIcons();
            }
        }
    }

    // Send Current Filtered 5-Story Briefing to Slack
    async function sendCurrentDigestToSlack() {
        const articles = state.articles || [];
        if (!articles || articles.length === 0) {
            showToast('No articles available to send in the current view.');
            return;
        }

        const btn = elements.sendSlackDigestBtn;
        const originalText = btn ? btn.innerHTML : null;
        if (btn) {
            btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-[#36C5F0]"></i><span class="hidden lg:inline">Posting...</span>`;
            btn.disabled = true;
            if (window.lucide) lucide.createIcons();
        }

        try {
            const payload = {
                location: state.currentLocation,
                topic: state.currentTopic,
                source: state.currentSource,
                limit: 5
            };

            const res = await fetch('/api/slack/send_digest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) {
                if (data.detail && data.detail.includes('Slack Webhook URL is not configured')) {
                    showToast('Please configure your Slack Webhook URL first.');
                    openSlackModal();
                    return;
                }
                throw new Error(data.detail || 'Failed to post briefing to Slack');
            }

            showToast(data.message || 'Briefing sent to Slack successfully!');
            closeSlackModal();
        } catch (err) {
            console.error('Slack digest dispatch error:', err);
            showToast(`Slack Error: ${err.message}`);
        } finally {
            if (btn && originalText) {
                btn.innerHTML = originalText;
                btn.disabled = false;
                if (window.lucide) lucide.createIcons();
            }
        }
    }

    // Send Dashboard Link to Slack Channel
    async function sendDashboardLinkToSlack() {
        const btn = elements.sendSlackDashboardBtn;
        const originalText = btn ? btn.innerHTML : null;
        if (btn) {
            btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-[#36C5F0]"></i><span class="hidden lg:inline">Sending Link...</span>`;
            btn.disabled = true;
            if (window.lucide) lucide.createIcons();
        }

        if (isStaticMode) {
            const webhook = localStorage.getItem('pulse_slack_webhook');
            const currentUrl = window.location.href;
            if (webhook) {
                try {
                    await fetch(webhook, {
                        method: 'POST',
                        mode: 'no-cors',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: `🌐 *PulseNews Live Dashboard*: ${currentUrl}\nLive aggregation across Google, MSN, Yahoo, X & Moneycontrol.`
                        })
                    });
                    showToast('Dashboard link dispatched to Slack webhook!');
                    closeSlackModal();
                } catch (e) {
                    console.warn('Slack webhook direct error:', e);
                }
            }
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(currentUrl);
                showToast('Dashboard link copied to clipboard!');
            } else {
                prompt('Copy PulseNews Dashboard URL:', currentUrl);
            }
            if (btn && originalText) {
                btn.innerHTML = originalText;
                btn.disabled = false;
                if (window.lucide) lucide.createIcons();
            }
            closeSlackModal();
            return;
        }

        try {
            const res = await fetch('/api/slack/send_dashboard', { method: 'POST' });
            const data = await res.json();
            if (!res.ok) {
                if (data.detail && data.detail.includes('Slack Webhook URL is not configured')) {
                    showToast('Please configure your Slack Webhook URL first.');
                    openSlackModal();
                    return;
                }
                throw new Error(data.detail || 'Failed to send dashboard link to Slack');
            }

            showToast(data.message || 'Dashboard link sent to Slack!');
            closeSlackModal();
        } catch (err) {
            console.error('Slack dashboard dispatch error:', err);
            showToast(`Slack Error: ${err.message}`);
        } finally {
            if (btn && originalText) {
                btn.innerHTML = originalText;
                btn.disabled = false;
                if (window.lucide) lucide.createIcons();
            }
        }
    }

    // Header & Modal Dashboard Send Buttons
    if (elements.sendSlackDashboardBtn) {
        elements.sendSlackDashboardBtn.addEventListener('click', sendDashboardLinkToSlack);
    }
    if (elements.sendDashboardNowBtn) {
        elements.sendDashboardNowBtn.addEventListener('click', sendDashboardLinkToSlack);
    }
    if (elements.sendDigestNowBtn) {
        elements.sendDigestNowBtn.addEventListener('click', sendCurrentDigestToSlack);
    }

    // Slack Modal Management
    async function openSlackModal() {
        if (!elements.slackModal) return;
        elements.slackModal.classList.remove('hidden');
        elements.slackModal.classList.add('flex');

        if (isStaticMode) {
            const webhook = localStorage.getItem('pulse_slack_webhook') || '';
            const channel = localStorage.getItem('pulse_slack_channel') || '';
            const botName = localStorage.getItem('pulse_slack_bot_name') || 'PulseNews Bot';
            if (elements.slackWebhookInput) elements.slackWebhookInput.value = webhook;
            if (elements.slackChannelInput) elements.slackChannelInput.value = channel;
            if (elements.slackBotNameInput) elements.slackBotNameInput.value = botName;
            if (elements.slackStatusBadge) {
                if (webhook) {
                    elements.slackStatusBadge.textContent = 'Active Webhook';
                    elements.slackStatusBadge.className = 'text-[10px] bg-emerald-950/80 text-emerald-300 px-2 py-0.5 rounded-full font-semibold border border-emerald-700/60';
                } else {
                    elements.slackStatusBadge.textContent = 'No Webhook Set';
                    elements.slackStatusBadge.className = 'text-[10px] bg-amber-950/80 text-amber-300 px-2 py-0.5 rounded-full font-semibold border border-amber-700/60';
                }
            }
            if (window.lucide) lucide.createIcons();
            return;
        }

        try {
            const res = await fetch('/api/slack/config');
            if (res.ok) {
                const config = await res.json();
                if (elements.slackWebhookInput) {
                    if (config.has_webhook) {
                        elements.slackWebhookInput.placeholder = `Current: ${config.slack_webhook_url_masked} (leave empty to keep)`;
                    } else {
                        elements.slackWebhookInput.placeholder = 'https://hooks.slack.com/services/T.../B.../...';
                    }
                }
                if (elements.slackChannelInput && config.slack_channel) {
                    elements.slackChannelInput.value = config.slack_channel;
                }
                if (elements.slackBotNameInput && config.slack_bot_name) {
                    elements.slackBotNameInput.value = config.slack_bot_name;
                }
                if (elements.slackStatusBadge) {
                    if (config.has_webhook) {
                        elements.slackStatusBadge.textContent = 'Active Webhook';
                        elements.slackStatusBadge.className = 'text-[10px] bg-emerald-950/80 text-emerald-300 px-2 py-0.5 rounded-full font-semibold border border-emerald-700/60';
                    } else {
                        elements.slackStatusBadge.textContent = 'No Webhook Set';
                        elements.slackStatusBadge.className = 'text-[10px] bg-amber-950/80 text-amber-300 px-2 py-0.5 rounded-full font-semibold border border-amber-700/60';
                    }
                }
            }
        } catch (err) {
            console.error('Error fetching Slack config:', err);
        }

        if (window.lucide) lucide.createIcons();
    }

    function closeSlackModal() {
        if (!elements.slackModal) return;
        elements.slackModal.classList.add('hidden');
        elements.slackModal.classList.remove('flex');
    }

    if (elements.openSlackModalBtn) {
        elements.openSlackModalBtn.addEventListener('click', openSlackModal);
    }
    if (elements.closeSlackModalBtn) {
        elements.closeSlackModalBtn.addEventListener('click', closeSlackModal);
    }
    if (elements.cancelSlackBtn) {
        elements.cancelSlackBtn.addEventListener('click', closeSlackModal);
    }

    // Save Slack Configuration
    if (elements.saveSlackBtn) {
        elements.saveSlackBtn.addEventListener('click', async () => {
            const webhook = elements.slackWebhookInput ? elements.slackWebhookInput.value.trim() : '';
            const channel = elements.slackChannelInput ? elements.slackChannelInput.value.trim() : '';
            const botName = elements.slackBotNameInput ? elements.slackBotNameInput.value.trim() : '';

            const payload = {};
            if (webhook) payload.slack_webhook_url = webhook;
            if (channel !== undefined) payload.slack_channel = channel;
            if (botName) payload.slack_bot_name = botName;

            if (isStaticMode) {
                localStorage.setItem('pulse_slack_webhook', webhook);
                localStorage.setItem('pulse_slack_channel', channel);
                localStorage.setItem('pulse_slack_bot_name', botName);
                showToast('Slack configuration saved to browser storage!');
                closeSlackModal();
                return;
            }

            try {
                const res = await fetch('/api/slack/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Failed to save configuration');

                showToast(data.message || 'Slack settings saved successfully!');
                closeSlackModal();
            } catch (err) {
                console.error('Save Slack config error:', err);
                showToast(`Failed to save: ${err.message}`);
            }
        });
    }

    // Test Slack Connection
    if (elements.testSlackBtn) {
        elements.testSlackBtn.addEventListener('click', async () => {
            const webhook = elements.slackWebhookInput ? elements.slackWebhookInput.value.trim() : '';
            const channel = elements.slackChannelInput ? elements.slackChannelInput.value.trim() : '';
            const botName = elements.slackBotNameInput ? elements.slackBotNameInput.value.trim() : '';

            // If user typed a new webhook in the input, save it first
            if (webhook) {
                try {
                    await fetch('/api/slack/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            slack_webhook_url: webhook,
                            slack_channel: channel,
                            slack_bot_name: botName
                        })
                    });
                } catch (e) {
                    console.error('Auto-save error before test:', e);
                }
            }

            const originalBtnText = elements.testSlackBtnText ? elements.testSlackBtnText.textContent : 'Send Test Message';
            if (elements.testSlackBtnText) elements.testSlackBtnText.textContent = 'Sending...';
            elements.testSlackBtn.disabled = true;

            if (isStaticMode) {
                const targetWebhook = webhook || localStorage.getItem('pulse_slack_webhook');
                if (!targetWebhook) {
                    showToast('Please enter a Slack Webhook URL first.');
                    if (elements.testSlackBtnText) elements.testSlackBtnText.textContent = originalBtnText;
                    elements.testSlackBtn.disabled = false;
                    return;
                }
                try {
                    await fetch(targetWebhook, {
                        method: 'POST',
                        mode: 'no-cors',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: '🎉 *PulseNews Connection Test* :white_check_mark:\nYour GitHub Pages live aggregator is successfully connected to this Slack channel!'
                        })
                    });
                    showToast('Test signal sent to Slack!');
                } catch (err) {
                    console.error('Slack test dispatch error:', err);
                    showToast('Webhook dispatch error. Check URL format.');
                } finally {
                    if (elements.testSlackBtnText) elements.testSlackBtnText.textContent = originalBtnText;
                    elements.testSlackBtn.disabled = false;
                }
                return;
            }

            try {
                const res = await fetch('/api/slack/test', { method: 'POST' });
                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.detail || 'Failed to send test message');
                }

                showToast(data.message || 'Test message posted to Slack channel!');
            } catch (err) {
                console.error('Slack test dispatch error:', err);
                showToast(`Test failed: ${err.message}`);
            } finally {
                if (elements.testSlackBtnText) elements.testSlackBtnText.textContent = originalBtnText;
                elements.testSlackBtn.disabled = false;
            }
        });
    }

    initTheme();
    loadConfig().then(() => {
        fetchNews();
    });
});
