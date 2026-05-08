const API_HOST = location.hostname || "localhost";
const API_CANDIDATES = [
  location.origin,
  `${location.protocol}//${API_HOST}:8000`,
  "http://localhost:8000",
];
let activeApiBase = null;

const state = {
  route: "home",
  currentTicker: "AAPL",
  theme: "dark",
  chart: null,
  compareChart: null,
  qaHistory: [],
  newsLimit: 8,
  watchlistId: null,
  watchRefresh: null,
  adminRefresh: null,
  research: {
    jobId: null,
    source: null,
    agents: new Map(),
    logs: [],
    result: null,
  },
};

const routes = {
  home: renderHome,
  stock: renderStock,
  screener: renderScreener,
  watchlist: renderWatchlist,
  research: renderResearch,
  compare: renderCompare,
  admin: renderAdmin,
};

const expectedAgents = [
  "news_event",
  "price_action",
  "fundamentals",
  "valuation",
  "sec_filings",
  "earnings",
  "market_context",
  "sentiment",
  "risk",
  "balanced_thesis",
  "insider_activity",
  "research_factors",
  "synthesizer",
  "evidence_auditor",
];

document.addEventListener("DOMContentLoaded", () => {
  bindShell();
  startHealthLoop();
  routeFromHash();
  window.addEventListener("hashchange", routeFromHash);
  if (window.lucide) window.lucide.createIcons();
});

function bindShell() {
  document.getElementById("dismiss-offline").addEventListener("click", () => {
    document.getElementById("offline-banner").classList.add("hidden");
  });
  document.getElementById("theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    document.body.classList.toggle("light", state.theme === "light");
    document.getElementById("theme-toggle").innerHTML = `<i data-lucide="${state.theme === "light" ? "moon" : "sun"}"></i>`;
    refreshIcons();
  });
  wireSearchBox(
    document.getElementById("global-search"),
    document.getElementById("global-suggestions"),
    (ticker) => loadStock(ticker),
  );
  document.getElementById("global-search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = document.getElementById("global-search").value.trim();
    if (!value) return;
    const ticker = await resolveTicker(value);
    loadStock(ticker || value.toUpperCase());
  });
}

function routeFromHash() {
  const route = (location.hash || "#home").replace("#", "") || "home";
  state.route = routes[route] ? route : "home";
  clearIntervalsForRoute();
  document.querySelectorAll(".nav-list a").forEach((item) => {
    item.classList.toggle("active", item.dataset.route === state.route);
  });
  routes[state.route]();
}

function clearIntervalsForRoute() {
  if (state.watchRefresh) {
    clearInterval(state.watchRefresh);
    state.watchRefresh = null;
  }
  if (state.adminRefresh) {
    clearInterval(state.adminRefresh);
    state.adminRefresh = null;
  }
}

async function startHealthLoop() {
  await checkHealth();
  setInterval(checkHealth, 15000);
}

async function checkHealth() {
  const banner = document.getElementById("offline-banner");
  const pill = document.getElementById("provider-pill");
  try {
    await api("/api/health", {}, false);
    banner.classList.add("hidden");
    pill.className = "status-pill live";
    pill.innerHTML = `<span class="status-dot"></span>Backend live`;
  } catch (error) {
    banner.classList.remove("hidden");
    pill.className = "status-pill offline";
    pill.innerHTML = `<span class="status-dot"></span>Backend offline`;
  }
}

async function api(path, options = {}, parseError = true) {
  const bases = activeApiBase ? [activeApiBase] : API_CANDIDATES;
  let lastError;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
      if (!response.ok) {
        const message = payload?.detail?.[0]?.msg || payload?.detail || payload?.error?.message || payload?.error || response.statusText;
        const error = new Error(parseError ? `${response.status}: ${message}` : response.statusText);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }
      activeApiBase = base;
      return payload;
    } catch (error) {
      lastError = error;
      if (activeApiBase) break;
    }
  }
  throw lastError || new Error("API unavailable");
}

function getData(payload) {
  return payload?.success && payload.data ? payload.data : payload;
}

function getCitations(payload) {
  return payload?.citations || payload?.data?.citations || payload?.result?.citations || [];
}

function getWarnings(payload) {
  return payload?.warnings || payload?.data?.warnings || payload?.result?.warnings || [];
}

function app(html) {
  document.getElementById("app").innerHTML = html;
  refreshIcons();
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function skeleton(count = 1, minHeight = 90) {
  return Array.from({ length: count }, () => `<div class="skeleton" style="min-height:${minHeight}px"></div>`).join("");
}

function errorCard(title, error, retry) {
  return `
    <div class="error-card">
      <div>
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(error?.message || String(error))}</p>
      </div>
      <button class="small-button" data-retry="${retry}">Retry</button>
    </div>
  `;
}

function emptyState(icon, text, hint = "") {
  return `
    <div class="empty-state">
      <div>
        <i data-lucide="${icon}"></i>
        <p>${escapeHtml(text)}</p>
        ${hint ? `<span>${escapeHtml(hint)}</span>` : ""}
      </div>
    </div>
  `;
}

function fmtMoney(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtNum(value, digits = 2) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function fmtPct(value, alreadyRatio = false) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  const pct = alreadyRatio ? num * 100 : num;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function pctClass(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num === 0) return "neutral";
  return num > 0 ? "positive" : "negative";
}

function abbr(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  const abs = Math.abs(num);
  if (abs >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(num / 1e3).toFixed(2)}K`;
  return fmtNum(num);
}

function relativeTime(value) {
  if (!value) return "";
  const then = new Date(value);
  if (Number.isNaN(then.getTime())) return String(value).slice(0, 16);
  const diff = Date.now() - then.getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 60) return `${Math.max(1, mins)}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function domain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "source";
  }
}

function citationChips(citations) {
  const items = (citations || []).filter((item) => item?.url || item?.title).slice(0, 12);
  if (!items.length) return "";
  return `<div class="citation-row">${items.map((item) => `
    <a class="citation-chip" href="${escapeAttr(item.url || "#")}" target="_blank" rel="noopener noreferrer" title="${escapeAttr(item.title || "Source")}">
      <span class="favicon-dot"></span>
      <span>${escapeHtml(item.provider || domain(item.url) || "source")}</span>
    </a>
  `).join("")}</div>`;
}

function warningList(warnings) {
  if (!warnings?.length) return "";
  return `<div class="citation-row">${warnings.slice(0, 6).map((warning) => `<span class="badge gold">${escapeHtml(warning)}</span>`).join("")}</div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function wireSearchBox(input, container, onPick) {
  const search = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) {
      container.classList.add("hidden");
      return;
    }
    try {
      const payload = await api(`/api/search?q=${encodeURIComponent(q)}&limit=7`);
      const results = payload.results || [];
      container.innerHTML = results.length ? results.map((item) => `
        <button type="button" class="suggestion" data-ticker="${escapeAttr(item.ticker)}">
          <span><strong>${escapeHtml(item.ticker)}</strong> ${escapeHtml(item.name || "")}</span>
          <span class="muted">${escapeHtml(item.exchange || item.match_type || "")}</span>
        </button>
      `).join("") : `<div class="suggestion"><span>No supported ticker found</span></div>`;
      container.classList.remove("hidden");
      container.querySelectorAll("[data-ticker]").forEach((button) => {
        button.addEventListener("click", () => {
          container.classList.add("hidden");
          input.value = "";
          onPick(button.dataset.ticker);
        });
      });
    } catch {
      container.classList.add("hidden");
    }
  }, 300);
  input.addEventListener("input", search);
}

async function resolveTicker(query) {
  const clean = query.trim().toUpperCase();
  if (/^[A-Z][A-Z0-9.-]{0,5}$/.test(clean)) return clean;
  try {
    const payload = await api(`/api/search?q=${encodeURIComponent(query)}&limit=10`);
    const exact = payload.results?.find((item) => item.name?.toLowerCase().includes(query.toLowerCase()));
    return (exact || payload.results?.[0])?.ticker;
  } catch {
    return clean;
  }
}

async function renderHome() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Market Overview</h1>
          <div class="view-subtitle">Live market snapshot from IMPERIA dataflows.</div>
        </div>
      </div>
      <div id="home-indices" class="grid-3">${skeleton(3, 120)}</div>
      <div class="grid-2">
        <div id="home-gainers" class="panel">${skeleton(1, 260)}</div>
        <div id="home-losers" class="panel">${skeleton(1, 260)}</div>
      </div>
      <div id="home-breadth" class="panel">${skeleton(1, 120)}</div>
    </section>
  `);
  try {
    const [summary, movers, breadth] = await Promise.all([
      api("/api/market/summary"),
      api("/api/market/movers?limit=5"),
      api("/api/market/breadth"),
    ]);
    drawIndices(summary.indices || []);
    drawMoverPanel("home-gainers", "Top Gainers", movers.gainers || summary.movers?.gainers || [], true);
    drawMoverPanel("home-losers", "Top Losers", movers.losers || summary.movers?.losers || [], false);
    drawBreadth(breadth || summary.breadth || {});
  } catch (error) {
    document.getElementById("home-indices").innerHTML = errorCard("Could not load market overview", error, "home");
    bindRetry("home", renderHome);
  }
}

function drawIndices(indices) {
  const preferred = ["SPY", "QQQ", "DIA"];
  const rows = preferred.map((ticker) => indices.find((item) => item.ticker === ticker || item.symbol === ticker)).filter(Boolean);
  document.getElementById("home-indices").innerHTML = rows.map((item) => `
    <div class="kpi-card">
      <div class="kpi-label">${escapeHtml(item.name || item.ticker)}</div>
      <div class="kpi-value">${fmtMoney(item.price)}</div>
      <div class="${pctClass(item.change_pct)}">${fmtMoney(item.change)} · ${fmtPct(item.change_pct)}</div>
    </div>
  `).join("") || emptyState("line-chart", "No index snapshot returned.");
}

function drawMoverPanel(id, title, rows, positive) {
  document.getElementById(id).innerHTML = `
    <div class="panel-header">
      <div class="panel-title"><i data-lucide="${positive ? "trending-up" : "trending-down"}"></i>${title}</div>
    </div>
    <div class="panel-body">
      ${rows.length ? `
        <table class="data-table">
          <thead><tr><th>Ticker</th><th>Price</th><th>% Change</th></tr></thead>
          <tbody>
            ${rows.slice(0, 5).map((item) => `
              <tr class="clickable" data-stock="${escapeAttr(item.ticker)}">
                <td><strong>${escapeHtml(item.ticker)}</strong></td>
                <td>${fmtMoney(item.price)}</td>
                <td class="${pctClass(item.change_pct)}">${fmtPct(item.change_pct)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : emptyState("list-minus", "No movers returned.")}
    </div>
  `;
  document.querySelectorAll(`#${id} [data-stock]`).forEach((row) => row.addEventListener("click", () => loadStock(row.dataset.stock)));
  refreshIcons();
}

function drawBreadth(breadth) {
  const adv = Number(breadth.advancing || 0);
  const dec = Number(breadth.declining || 0);
  const total = Math.max(adv + dec + Number(breadth.unchanged || 0), 1);
  const width = Math.round((adv / total) * 100);
  document.getElementById("home-breadth").innerHTML = `
    <div class="panel-header">
      <div class="panel-title"><i data-lucide="bar-chart-3"></i>Market Breadth</div>
      <span class="badge">${fmtNum(total, 0)} tracked</span>
    </div>
    <div class="panel-body">
      <div class="breadth-track"><div class="breadth-fill" style="width:${width}%"></div></div>
      <div class="quote-meta" style="margin-top:10px">
        <span class="positive">${fmtNum(adv, 0)} advancing</span>
        <span class="negative">${fmtNum(dec, 0)} declining</span>
        <span>${fmtNum(breadth.unchanged || 0, 0)} unchanged</span>
      </div>
      ${warningList(breadth.warnings)}
    </div>
  `;
  refreshIcons();
}

function loadStock(ticker) {
  state.currentTicker = ticker.toUpperCase();
  state.newsLimit = 8;
  if (location.hash !== "#stock") location.hash = "#stock";
  else renderStock();
}

async function renderStock() {
  const ticker = state.currentTicker || "AAPL";
  app(`
    <section class="view">
      <form id="stock-search-form" class="search-card" autocomplete="off">
        <i data-lucide="search"></i>
        <input id="stock-search" type="search" placeholder="Search for a stock, e.g. Apple, NVDA, Tesla..." />
        <button class="primary-button" type="submit">Search</button>
        <div id="stock-suggestions" class="suggestions hidden"></div>
      </form>
      <div id="quote-strip">${skeleton(1, 108)}</div>
      <div class="stock-layout">
        <div class="column-stack">
          <div id="chart-panel" class="panel">${skeleton(1, 380)}</div>
          <div id="metrics-panel" class="panel">${skeleton(1, 250)}</div>
          <div id="news-panel" class="panel">${skeleton(1, 360)}</div>
          <div id="ask-panel" class="panel"></div>
        </div>
        <div class="column-stack">
          <div id="profile-panel" class="panel">${skeleton(1, 270)}</div>
          <div id="earnings-panel" class="panel">${skeleton(1, 210)}</div>
          <div id="sentiment-panel" class="panel">${skeleton(1, 220)}</div>
          <div id="checklist-panel" class="panel">${skeleton(1, 260)}</div>
        </div>
      </div>
    </section>
  `);
  wireSearchBox(document.getElementById("stock-search"), document.getElementById("stock-suggestions"), loadStock);
  document.getElementById("stock-search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = document.getElementById("stock-search").value.trim();
    if (!value) return;
    loadStock(await resolveTicker(value));
  });
  renderAskPanel(ticker);
  await Promise.allSettled([
    loadQuote(ticker),
    loadChart(ticker, "7d"),
    loadMetrics(ticker),
    loadNews(ticker),
    loadProfile(ticker),
    loadEarnings(ticker),
    loadSentiment(ticker),
    loadChecklist(ticker),
  ]);
}

async function loadQuote(ticker) {
  try {
    const [quote, profile] = await Promise.all([
      api(`/api/quote/${ticker}`),
      api(`/api/stock/${ticker}/profile`).catch(() => ({})),
    ]);
    const name = profile.name || quote.name || ticker;
    document.getElementById("quote-strip").innerHTML = `
      <div class="quote-strip">
        <div>
          <div class="quote-meta"><span class="badge">${escapeHtml(ticker)}</span><span>${escapeHtml(name)}</span><span>${escapeHtml(profile.exchange || quote.exchange || "")}</span></div>
          <div class="price-value">${fmtMoney(quote.price)}</div>
          <div class="${pctClass(quote.changePct)}">${fmtMoney(quote.change)} · ${fmtPct(quote.changePct)}</div>
        </div>
        <div class="quote-meta">
          <span>Volume ${abbr(quote.volume)}</span>
          <span>Market cap ${abbr(profile.market_cap || quote.marketCap)}</span>
          <span>Day ${fmtMoney(quote.dayLow)}–${fmtMoney(quote.dayHigh)}</span>
        </div>
      </div>
    `;
  } catch (error) {
    document.getElementById("quote-strip").innerHTML = errorCard("Could not load quote", error, "quote");
    bindRetry("quote", () => loadQuote(ticker));
  }
}

async function loadChart(ticker, period) {
  const panel = document.getElementById("chart-panel");
  panel.innerHTML = `
    <div class="panel-header">
      <div class="panel-title"><i data-lucide="line-chart"></i>Price Chart</div>
      <div class="periods">
        ${["1D", "7D", "1M", "3M", "1Y"].map((label) => `<button class="seg-button ${periodLabel(period) === label ? "active" : ""}" data-period="${label}">${label}</button>`).join("")}
      </div>
    </div>
    <div class="panel-body"><div class="chart-wrap"><canvas id="price-chart"></canvas></div></div>
  `;
  panel.querySelectorAll("[data-period]").forEach((button) => button.addEventListener("click", () => loadChart(ticker, periodValue(button.dataset.period))));
  refreshIcons();
  try {
    const payload = period === "1d"
      ? await api(`/api/stock/${ticker}/intraday`)
      : await api(`/api/stock/${ticker}/chart?period=${period}`);
    const points = payload.points || [];
    const labels = points.map((point) => String(point.date).slice(0, 16));
    const prices = points.map((point) => point.close);
    const volumes = points.map((point) => point.volume || 0);
    if (state.chart) state.chart.destroy();
    state.chart = new Chart(document.getElementById("price-chart"), {
      data: {
        labels,
        datasets: [
          {
            type: "line",
            label: `${ticker} close`,
            data: prices,
            borderColor: "#20b2aa",
            backgroundColor: "rgba(32,178,170,0.1)",
            tension: 0.35,
            pointRadius: 0,
            yAxisID: "price",
          },
          {
            type: "bar",
            label: "Volume",
            data: volumes,
            backgroundColor: "rgba(136,136,146,0.18)",
            yAxisID: "volume",
          },
        ],
      },
      options: chartOptions("price", "volume"),
    });
  } catch (error) {
    panel.querySelector(".panel-body").innerHTML = errorCard("Could not load chart", error, "chart");
    bindRetry("chart", () => loadChart(ticker, period));
  }
}

function periodValue(label) {
  return { "1D": "1d", "7D": "7d", "1M": "1mo", "3M": "3mo", "1Y": "1y" }[label] || "7d";
}

function periodLabel(value) {
  return { "1d": "1D", "7d": "7D", "1mo": "1M", "3mo": "3M", "1y": "1Y" }[value] || "7D";
}

function chartOptions(left = "price", right = "volume") {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { labels: { color: getComputedStyle(document.body).getPropertyValue("--text-muted") } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.dataset.type === "bar" ? abbr(ctx.raw) : fmtMoney(ctx.raw)}` } },
    },
    scales: {
      [left]: { position: "left", grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#888892" } },
      [right]: { position: "right", display: false, grid: { drawOnChartArea: false } },
      x: { grid: { display: false }, ticks: { color: "#888892", maxTicksLimit: 7 } },
    },
  };
}

async function loadMetrics(ticker) {
  try {
    const payload = await api(`/api/stock/${ticker}/ratios`);
    const metrics = payload.metrics || {};
    const rows = [
      ["P/E", metrics.pe],
      ["Forward P/E", metrics.forward_pe],
      ["EPS", metrics.eps],
      ["Revenue Growth", metrics.revenue_growth, true],
      ["ROE", metrics.roe, true],
      ["FCF Margin", metrics.free_cash_flow_margin, true],
      ["Debt/Equity", metrics.debt_to_equity],
      ["EV/EBITDA", metrics.ev_to_ebitda],
    ];
    document.getElementById("metrics-panel").innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="calculator"></i>Key Metrics</div><span class="badge">${escapeHtml(payload.sources?.[0] || "computed")}</span></div>
      <div class="panel-body">
        <div class="metric-grid">${rows.map(([label, value, pct]) => `
          <div class="metric-card">
            <div class="metric-label">${label}</div>
            <div class="metric-value">${pct ? fmtPct(value, true) : fmtNum(value)}</div>
            <div class="spark"></div>
          </div>
        `).join("")}</div>
        ${warningList(payload.warnings)}
        ${citationChips(payload.citations)}
      </div>
    `;
    refreshIcons();
  } catch (error) {
    document.getElementById("metrics-panel").innerHTML = errorCard("Could not load metrics", error, "metrics");
    bindRetry("metrics", () => loadMetrics(ticker));
  }
}

async function loadNews(ticker) {
  try {
    const payload = await api(`/api/stock/${ticker}/news?window=today&limit=20`);
    const articles = payload.articles || [];
    document.getElementById("news-panel").innerHTML = `
      <div class="panel-header">
        <div class="panel-title"><i data-lucide="newspaper"></i>Recent News</div>
        <span class="badge">${escapeHtml(payload.window || "today")}</span>
      </div>
      <div class="panel-body">
        ${articles.length ? `<div class="news-list">${articles.slice(0, state.newsLimit).map(newsItem).join("")}</div>` : emptyState("newspaper", "No news found for this window.", "Try another ticker or time window.")}
        ${articles.length > state.newsLimit ? `<button id="load-more-news" class="ghost-button" style="margin-top:12px">Load more</button>` : ""}
        ${citationChips(payload.citations)}
      </div>
    `;
    document.getElementById("load-more-news")?.addEventListener("click", () => {
      state.newsLimit += 6;
      loadNews(ticker);
    });
    refreshIcons();
  } catch (error) {
    document.getElementById("news-panel").innerHTML = errorCard("Could not load news", error, "news");
    bindRetry("news", () => loadNews(ticker));
  }
}

function newsItem(item) {
  const sentimentIcon = item.sentiment_label === "bullish" ? "trending-up" : item.sentiment_label === "bearish" ? "trending-down" : "minus";
  return `
    <a class="news-item" href="${escapeAttr(item.url || "#")}" target="_blank" rel="noopener noreferrer">
      <div class="news-head">
        <div class="news-title">${escapeHtml(item.title || "Untitled article")}</div>
        <i data-lucide="${sentimentIcon}"></i>
      </div>
      <div class="quote-meta">
        <span class="badge">${escapeHtml(item.source || item.provider || "news")}</span>
        <span>${escapeHtml(relativeTime(item.published_at))}</span>
      </div>
    </a>
  `;
}

async function loadProfile(ticker) {
  try {
    const profile = await api(`/api/stock/${ticker}/profile`);
    document.getElementById("profile-panel").innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="building-2"></i>Company Profile</div><span class="badge">${escapeHtml(profile.sector || "sector")}</span></div>
      <div class="panel-body">
        <div class="quote-meta"><span>${escapeHtml(profile.industry || "—")}</span><span>${escapeHtml(profile.exchange || "")}</span><span>Market cap ${abbr(profile.market_cap)}</span></div>
        <p id="profile-summary" class="profile-summary">${escapeHtml(profile.summary || "No company description returned.")}</p>
        <div class="chips">
          ${profile.website ? `<a class="chip" href="${escapeAttr(profile.website)}" target="_blank" rel="noopener noreferrer">Website</a>` : ""}
          <button id="expand-profile" class="chip" type="button">Expand</button>
        </div>
      </div>
    `;
    document.getElementById("expand-profile").addEventListener("click", () => {
      document.getElementById("profile-summary").classList.toggle("expanded");
    });
    refreshIcons();
  } catch (error) {
    document.getElementById("profile-panel").innerHTML = errorCard("Could not load profile", error, "profile");
    bindRetry("profile", () => loadProfile(ticker));
  }
}

async function loadEarnings(ticker) {
  try {
    const [next, history] = await Promise.all([
      api(`/api/stock/${ticker}/next-earnings`),
      api(`/api/earnings/${ticker}/history`).catch(() => ({ history: [] })),
    ]);
    const rows = (history.history || []).slice(0, 4);
    document.getElementById("earnings-panel").innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="calendar-days"></i>Earnings</div><span class="badge gold">${escapeHtml(next.report_date || next.event?.report_date || "TBD")}</span></div>
      <div class="panel-body">
        <div class="quote-meta"><span>EPS estimate ${fmtNum(next.estimated_eps || next.event?.estimated_eps)}</span><span>${escapeHtml(next.time_of_day || "")}</span></div>
        <div class="news-list" style="margin-top:12px">
          ${rows.length ? rows.map((item) => `<div class="earnings-row"><span>${escapeHtml(item.fiscal_period || item.report_date)}</span><span class="badge ${item.beat_miss === "beat" ? "positive" : item.beat_miss === "miss" ? "negative" : ""}">${escapeHtml(item.beat_miss || "reported")}</span></div>`).join("") : emptyState("calendar-x", "No earnings history returned.")}
        </div>
      </div>
    `;
    refreshIcons();
  } catch (error) {
    document.getElementById("earnings-panel").innerHTML = errorCard("Could not load earnings", error, "earnings");
    bindRetry("earnings", () => loadEarnings(ticker));
  }
}

async function loadSentiment(ticker) {
  try {
    const payload = await api(`/api/stock/${ticker}/sentiment?window=today`);
    const data = getData(payload);
    const label = data.sentiment_label || data.research_sentiment || "uncertain";
    const score = Number(data.confidence_score || 0);
    const poly = data.signals?.polymarket || {};
    document.getElementById("sentiment-panel").innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="radio-tower"></i>Sentiment</div><span class="badge">${escapeHtml(label)}</span></div>
      <div class="panel-body">
        <div class="sentiment-label ${label === "bullish" ? "positive" : label === "bearish" ? "negative" : ""}">${escapeHtml(label)}</div>
        <div class="sentiment-track" style="margin:10px 0"><div class="sentiment-fill" style="width:${Math.max(5, Math.min(100, score))}%"></div></div>
        <p class="muted">${escapeHtml(data.summary || "Sentiment summary unavailable.")}</p>
        ${poly?.signals?.length ? `<span class="badge">Polymarket ${fmtPct(poly.signals[0].probability || poly.signals[0].yes_price || 0, true)}</span>` : `<span class="badge">No relevant Polymarket market</span>`}
        ${warningList(payload.warnings)}
        ${citationChips(payload.citations)}
      </div>
    `;
    refreshIcons();
  } catch (error) {
    document.getElementById("sentiment-panel").innerHTML = errorCard("Could not load sentiment", error, "sentiment");
    bindRetry("sentiment", () => loadSentiment(ticker));
  }
}

async function loadChecklist(ticker) {
  try {
    const payload = await api(`/api/stock/${ticker}/investor-checklist`);
    const data = getData(payload);
    const groups = [
      ["Valuation", data.valuation_checklist],
      ["Growth", data.growth_checklist],
      ["Profitability", data.profitability_checklist],
      ["Balance sheet", data.balance_sheet_checklist],
      ["Earnings", data.earnings_checklist],
      ["Risks", data.risk_checklist],
      ["News", data.news_checklist],
    ];
    document.getElementById("checklist-panel").innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="list-checks"></i>Research Factors</div><span class="badge">not advice</span></div>
      <div class="panel-body">
        <div class="checklist-list">
          ${groups.flatMap(([name, items]) => (items || []).slice(0, 2).map((item) => `
            <div class="checklist-row">
              <span><strong>${escapeHtml(name)}</strong><br><span class="muted">${escapeHtml(item)}</span></span>
              <span class="badge gold">Review</span>
            </div>
          `)).join("") || emptyState("clipboard-list", "No checklist returned.")}
        </div>
        ${citationChips(payload.citations)}
      </div>
    `;
    refreshIcons();
  } catch (error) {
    document.getElementById("checklist-panel").innerHTML = errorCard("Could not load research factors", error, "checklist");
    bindRetry("checklist", () => loadChecklist(ticker));
  }
}

function renderAskPanel(ticker) {
  document.getElementById("ask-panel").innerHTML = `
    <div class="panel-header"><div class="panel-title"><i data-lucide="sparkles"></i>Ask IMPERIA</div><span class="badge">Fast mode</span></div>
    <div class="panel-body">
      <form id="ask-form" class="ask-form">
        <div class="ask-row">
          <input class="input" id="ask-input" placeholder="Ask anything about ${escapeAttr(ticker)}..." />
          <button class="primary-button" type="submit">Ask</button>
        </div>
      </form>
      <div id="qa-list" class="qa-list" style="margin-top:12px">
        ${state.qaHistory.length ? state.qaHistory.map(qaItem).join("") : emptyState("message-square", `Ask a question about ${ticker}.`, "Answers include citations when sources are available.")}
      </div>
      <div class="disclaimer">For educational and research purposes only. Not investment advice.</div>
    </div>
  `;
  document.getElementById("ask-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("ask-input");
    const query = input.value.trim();
    if (!query) return;
    input.value = "";
    const item = { ticker, query, answer: "", citations: [], warnings: [], loading: true };
    state.qaHistory.unshift(item);
    renderAskPanel(ticker);
    try {
      const payload = await api("/api/ask", { method: "POST", body: JSON.stringify({ ticker, query }) });
      item.answer = payload.answer || payload.data?.answer || "No answer returned.";
      item.citations = getCitations(payload);
      item.warnings = getWarnings(payload);
      item.loading = false;
      renderAskPanel(ticker);
      typeAnswer(document.querySelector("[data-latest-answer]"), item.answer);
    } catch (error) {
      item.answer = `Error: ${error.message}`;
      item.loading = false;
      renderAskPanel(ticker);
    }
  });
  refreshIcons();
}

function qaItem(item, index) {
  const answerId = index === 0 ? "data-latest-answer" : "";
  return `
    <div class="qa-item">
      <div class="muted">${escapeHtml(item.ticker)} · ${escapeHtml(item.query)}</div>
      <p ${answerId}>${item.loading ? "Researching..." : escapeHtml(item.answer)}</p>
      ${citationChips(item.citations)}
      ${warningList(item.warnings)}
      <div class="disclaimer">For educational and research purposes only. Not investment advice.</div>
    </div>
  `;
}

function typeAnswer(element, text) {
  if (!element) return;
  element.textContent = "";
  let i = 0;
  const timer = setInterval(() => {
    element.textContent += text[i] || "";
    i += 1;
    if (i >= text.length) clearInterval(timer);
  }, 8);
}

async function renderResearch() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Deep Research</h1>
          <div class="view-subtitle">Background expert-agent panel with live SSE progress.</div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body">
          <form id="deep-form" class="deep-form">
            <div class="form-grid">
              <input id="deep-ticker" class="input" value="${escapeAttr(state.currentTicker || "AAPL")}" placeholder="Ticker" />
              <select id="deep-window" class="input">
                <option value="today">Today</option>
                <option value="past_week" selected>Past Week</option>
                <option value="past_month">Past Month</option>
                <option value="this_quarter">Past Quarter</option>
              </select>
            </div>
            <textarea id="deep-question" placeholder="What do you want to research?">Analyze ${escapeHtml(state.currentTicker || "AAPL")} with recent news, fundamentals, filings, sentiment, risks, and what to watch next.</textarea>
            <div class="checkbox-grid">
              ${["fundamentals", "earnings", "filings", "news", "sentiment", "macro"].map((item) => `
                <label class="check-pill"><input type="checkbox" name="focus" value="${item}" checked /> ${item}</label>
              `).join("")}
            </div>
            <button class="primary-button" type="submit"><i data-lucide="play"></i>Run Deep Research</button>
          </form>
        </div>
      </div>
      <div id="research-progress"></div>
      <div id="research-report"></div>
    </section>
  `);
  document.getElementById("deep-form").addEventListener("submit", submitResearch);
  if (state.research.jobId) renderResearchProgress();
  refreshIcons();
}

async function submitResearch(event) {
  event.preventDefault();
  const ticker = document.getElementById("deep-ticker").value.trim().toUpperCase();
  const question = document.getElementById("deep-question").value.trim();
  const windowValue = document.getElementById("deep-window").value;
  const focus = Array.from(document.querySelectorAll("input[name='focus']:checked")).map((item) => item.value);
  state.research = { jobId: null, source: null, agents: new Map(), logs: [], result: null };
  expectedAgents.forEach((agent) => state.research.agents.set(agent, "pending"));
  renderResearchProgress();
  try {
    const payload = await api("/api/research", {
      method: "POST",
      body: JSON.stringify({ ticker, question, window: windowValue, focus }),
    });
    state.research.jobId = payload.research_id || payload.id || payload.data?.research_id;
    state.currentTicker = ticker;
    logResearch("queued", { research_id: state.research.jobId });
    renderResearchProgress();
    openResearchStream(state.research.jobId);
  } catch (error) {
    document.getElementById("research-progress").innerHTML = errorCard("Could not submit deep research", error, "deep");
    bindRetry("deep", () => document.getElementById("deep-form").requestSubmit());
  }
}

function renderResearchProgress() {
  const done = Array.from(state.research.agents.values()).filter((status) => status === "done").length;
  const total = Math.max(state.research.agents.size, expectedAgents.length);
  const pct = Math.round((done / total) * 100);
  document.getElementById("research-progress").innerHTML = `
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title"><i data-lucide="workflow"></i>Agent Progress</div>
        <span class="badge">${escapeHtml(state.research.jobId || "not submitted")}</span>
      </div>
      <div class="panel-body">
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="agent-grid" style="margin-top:14px">
          ${Array.from(state.research.agents.entries()).map(([agent, status]) => `
            <div class="agent-card ${status}">
              <span>${agentLabel(agent)}</span>
              <span class="agent-status">${status === "done" ? "DONE" : status === "running" ? "RUNNING" : status === "error" ? "ERROR" : "PENDING"}</span>
            </div>
          `).join("")}
        </div>
        <div class="log-list" style="margin-top:14px">
          ${state.research.logs.slice(-5).map((line) => `<div class="log-line">${escapeHtml(line)}</div>`).join("") || `<div class="log-line muted">Waiting for research events...</div>`}
        </div>
      </div>
    </div>
  `;
  refreshIcons();
}

function openResearchStream(jobId) {
  if (state.research.source) state.research.source.close();
  const source = new EventSource(`${activeApiBase || location.origin}/api/research/${jobId}/stream`);
  state.research.source = source;
  const events = ["queued", "running", "data_collection_started", "data_collection_completed", "agent_started", "agent_completed", "agent_failed", "synthesis_started", "synthesis_completed", "audit_started", "completed", "failed", "status"];
  events.forEach((eventName) => {
    source.addEventListener(eventName, (event) => handleResearchEvent(eventName, event.data));
  });
  source.onerror = () => {
    logResearch("stream_reconnecting", {});
    pollResearch(jobId);
  };
}

async function handleResearchEvent(eventName, dataText) {
  let payload = {};
  try { payload = JSON.parse(dataText); } catch { payload = {}; }
  if (payload.agent) {
    const key = String(payload.agent).toLowerCase();
    state.research.agents.set(key, eventName === "agent_failed" ? "error" : eventName === "agent_started" ? "running" : "done");
  }
  if (eventName === "synthesis_started") state.research.agents.set("synthesizer", "running");
  if (eventName === "synthesis_completed") state.research.agents.set("synthesizer", "done");
  if (eventName === "audit_started") state.research.agents.set("evidence_auditor", "running");
  logResearch(eventName, payload);
  renderResearchProgress();
  if (eventName === "completed" || payload.status === "completed") {
    state.research.source?.close();
    await fetchResearchReport(state.research.jobId);
  }
}

async function pollResearch(jobId) {
  try {
    const payload = await api(`/api/research/${jobId}`);
    if (payload.status === "completed") await fetchResearchReport(jobId);
  } catch {
    /* best effort */
  }
}

function logResearch(eventName, payload) {
  state.research.logs.push(`${new Date().toLocaleTimeString()} · ${eventName}${payload.agent ? ` · ${payload.agent}` : ""}`);
  state.research.logs = state.research.logs.slice(-40);
}

async function fetchResearchReport(jobId) {
  const payload = await api(`/api/research/${jobId}`);
  const result = payload.result || payload;
  const report = result.final_report || result.final_report_json || result;
  state.research.result = result;
  expectedAgents.forEach((agent) => {
    if (result.agent_outputs?.[agent]) state.research.agents.set(agent, "done");
  });
  renderResearchProgress();
  renderResearchReport(report, result);
}

function renderResearchReport(report, result) {
  const citations = result.citations || report.citations || [];
  const sections = [
    ["Executive Summary", report.executive_summary || report.summary],
    ["Bull Case", listText(report.bullish_factors || report.balanced_thesis?.bull_view?.supporting_evidence)],
    ["Bear Case", listText(report.bearish_factors || report.balanced_thesis?.bear_view?.supporting_evidence)],
    ["Risk Factors", listText(report.key_risks)],
    ["Fundamentals Analysis", result.agent_outputs?.fundamentals?.summary],
    ["News & Sentiment Analysis", [result.agent_outputs?.news_event?.summary, result.agent_outputs?.sentiment?.summary].filter(Boolean).join("\n\n")],
    ["SEC Filings Insights", result.agent_outputs?.sec_filings?.summary],
    ["Macro Context", result.agent_outputs?.market_context?.summary],
    ["Final Analyst Note", report.final_research_summary],
  ];
  document.getElementById("research-report").innerHTML = `
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title"><i data-lucide="file-text"></i>Research Report</div>
        <button id="export-md" class="ghost-button"><i data-lucide="download"></i>Export as Markdown</button>
      </div>
      <div class="panel-body report-sections">
        ${sections.map(([title, body], index) => `
          <details class="report-section" ${index === 0 ? "open" : ""}>
            <summary>${escapeHtml(title)}</summary>
            <p>${escapeHtml(body || "No section data returned.")}</p>
            ${citationChips(citations)}
          </details>
        `).join("")}
        ${warningList(result.warnings)}
        <div class="disclaimer">For educational and research purposes only. Not investment advice.</div>
      </div>
    </div>
  `;
  document.getElementById("export-md").addEventListener("click", () => exportMarkdown(sections, result.ticker || state.currentTicker));
  refreshIcons();
}

function exportMarkdown(sections, ticker) {
  const md = [`# IMPERIA Research Report: ${ticker}`, "", "_For educational and research purposes only. Not investment advice._", ""]
    .concat(sections.flatMap(([title, body]) => [`## ${title}`, "", body || "No section data returned.", ""]))
    .join("\n");
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `imperia-${ticker}-research.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function agentLabel(agent) {
  return agent.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

function listText(items) {
  return Array.isArray(items) ? items.join("\n") : items || "";
}

function renderScreener() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Stock Screener</h1>
          <div class="view-subtitle">Natural-language criteria parsed into structured filters.</div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body">
          <form id="screener-form" class="ask-form">
            <textarea id="screener-query" placeholder="Find me profitable tech stocks with P/E under 25..."></textarea>
            <button class="primary-button" type="submit">Run Screener</button>
          </form>
          <div class="chips" style="margin-top:12px">
            ${["High growth tech", "Dividend stocks", "Undervalued energy", "Profitable technology stocks with P/E under 25"].map((text) => `<button class="chip" data-example="${escapeAttr(text)}">${escapeHtml(text)}</button>`).join("")}
          </div>
        </div>
      </div>
      <div id="screener-results" class="panel">${emptyState("search", "Try: tech stocks with high FCF margin")}</div>
    </section>
  `);
  document.querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", () => {
    document.getElementById("screener-query").value = button.dataset.example;
  }));
  document.getElementById("screener-form").addEventListener("submit", runScreener);
  refreshIcons();
}

async function runScreener(event) {
  event.preventDefault();
  const query = document.getElementById("screener-query").value.trim();
  const target = document.getElementById("screener-results");
  if (!query) return;
  target.innerHTML = skeleton(1, 320);
  try {
    const payload = await api("/api/screener/nl", { method: "POST", body: JSON.stringify({ query }) });
    const rows = payload.results || [];
    target.innerHTML = `
      <div class="panel-header"><div class="panel-title"><i data-lucide="table"></i>Results</div><span class="badge">${rows.length} matches</span></div>
      <div class="panel-body">
        ${rows.length ? `<table class="data-table">
          <thead><tr><th>Ticker</th><th>Name</th><th>Sector</th><th>Price</th><th>P/E</th><th>Market Cap</th><th>Revenue Growth</th><th>Match</th></tr></thead>
          <tbody>${rows.map((item) => `
            <tr class="clickable" data-stock="${escapeAttr(item.ticker)}">
              <td><strong>${escapeHtml(item.ticker)}</strong></td>
              <td>${escapeHtml(item.name || "—")}</td>
              <td>${escapeHtml(item.sector || "—")}</td>
              <td>${fmtMoney(item.price)}</td>
              <td>${fmtNum(item.pe)}</td>
              <td>${abbr(item.market_cap)}</td>
              <td>${fmtPct(item.revenue_growth, true)}</td>
              <td>${fmtNum(item.match_score || item.score || 0)}</td>
            </tr>`).join("")}</tbody>
        </table>` : emptyState("search-x", "No stocks matched this query.", "Try: profitable technology stocks with P/E under 25.")}
      </div>
    `;
    target.querySelectorAll("[data-stock]").forEach((row) => row.addEventListener("click", () => loadStock(row.dataset.stock)));
    refreshIcons();
  } catch (error) {
    target.innerHTML = errorCard("Screener query failed", error, "screener");
    bindRetry("screener", () => runScreener(event));
  }
}

async function renderWatchlist() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Watchlist</h1>
          <div class="view-subtitle">Saved tickers with refreshed quotes.</div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body">
          <form id="watch-form" class="inline-form">
            <input id="watch-input" class="input" placeholder="Add ticker or company name" />
            <button class="primary-button" type="submit">Add</button>
          </form>
        </div>
      </div>
      <div id="watch-content">${skeleton(3, 100)}</div>
    </section>
  `);
  document.getElementById("watch-form").addEventListener("submit", addWatchTicker);
  await ensureWatchlist();
  await loadWatchlistQuotes();
  state.watchRefresh = setInterval(loadWatchlistQuotes, 60000);
}

async function ensureWatchlist() {
  const lists = await api("/api/watchlist");
  const existing = lists.find((item) => item.name === "IMPERIA Watchlist") || lists[0];
  if (existing) {
    state.watchlistId = existing.id;
    return;
  }
  const created = await api("/api/watchlist", { method: "POST", body: JSON.stringify({ name: "IMPERIA Watchlist", tickers: [] }) });
  state.watchlistId = created.id;
}

async function addWatchTicker(event) {
  event.preventDefault();
  const input = document.getElementById("watch-input");
  const ticker = await resolveTicker(input.value);
  input.value = "";
  if (!ticker) return;
  await ensureWatchlist();
  await api(`/api/watchlist/${state.watchlistId}/tickers`, { method: "POST", body: JSON.stringify({ ticker }) });
  await loadWatchlistQuotes();
}

async function loadWatchlistQuotes() {
  const target = document.getElementById("watch-content");
  try {
    await ensureWatchlist();
    const quotes = await api(`/api/watchlist/${state.watchlistId}/quotes`);
    target.innerHTML = quotes.length ? `
      <div class="grid-3">
        ${quotes.map((item) => `
          <div class="watch-card">
            <div class="clickable" data-stock="${escapeAttr(item.ticker)}">
              <strong>${escapeHtml(item.ticker)}</strong>
              <div class="muted">${escapeHtml(item.name || "")}</div>
              <div class="metric-value">${fmtMoney(item.price)}</div>
              <div class="${pctClass(item.change_pct)}">${fmtPct(item.change_pct)}</div>
            </div>
            <button class="icon-button" data-remove="${escapeAttr(item.ticker)}" aria-label="Remove ${escapeAttr(item.ticker)}"><i data-lucide="trash-2"></i></button>
          </div>
        `).join("")}
      </div>` : emptyState("star", "Your watchlist is empty.", "Search for a stock to add it.");
    target.querySelectorAll("[data-stock]").forEach((row) => row.addEventListener("click", () => loadStock(row.dataset.stock)));
    target.querySelectorAll("[data-remove]").forEach((button) => button.addEventListener("click", async () => {
      await api(`/api/watchlist/${state.watchlistId}/tickers/${button.dataset.remove}`, { method: "DELETE" });
      await loadWatchlistQuotes();
    }));
    refreshIcons();
  } catch (error) {
    target.innerHTML = errorCard("Could not load watchlist", error, "watchlist");
    bindRetry("watchlist", loadWatchlistQuotes);
  }
}

function renderCompare() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Compare Stocks</h1>
          <div class="view-subtitle">Side-by-side fundamentals, valuation, sentiment, and chart context.</div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-body">
          <form id="compare-form" class="compare-form">
            <div class="form-grid">
              <input id="compare-a" class="input" value="AMD" placeholder="Stock A" />
              <input id="compare-b" class="input" value="NVDA" placeholder="Stock B" />
            </div>
            <button class="primary-button" type="submit">Compare</button>
          </form>
        </div>
      </div>
      <div id="compare-output"></div>
    </section>
  `);
  document.getElementById("compare-form").addEventListener("submit", runCompare);
  refreshIcons();
}

async function runCompare(event) {
  event.preventDefault();
  const a = (await resolveTicker(document.getElementById("compare-a").value)).toUpperCase();
  const b = (await resolveTicker(document.getElementById("compare-b").value)).toUpperCase();
  const target = document.getElementById("compare-output");
  target.innerHTML = skeleton(2, 280);
  try {
    const [payload, chartA, chartB] = await Promise.all([
      api(`/api/compare?ticker_a=${a}&ticker_b=${b}`),
      api(`/api/stock/${a}/chart?period=1mo`),
      api(`/api/stock/${b}/chart?period=1mo`),
    ]);
    const data = getData(payload);
    const rows = flattenCompare(data, a, b);
    target.innerHTML = `
      <div class="panel">
        <div class="panel-header"><div class="panel-title"><i data-lucide="scale"></i>${a} vs ${b}</div></div>
        <div class="panel-body"><div class="chart-wrap"><canvas id="compare-chart"></canvas></div></div>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="panel-header"><div class="panel-title"><i data-lucide="table-properties"></i>Comparison Table</div></div>
        <div class="panel-body">
          <table class="data-table">
            <thead><tr><th>Metric</th><th>${a}</th><th>${b}</th></tr></thead>
            <tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.metric)}</td><td>${escapeHtml(row.a)}</td><td>${escapeHtml(row.b)}</td></tr>`).join("")}</tbody>
          </table>
          ${citationChips(payload.citations)}
        </div>
      </div>
    `;
    drawCompareChart(a, b, chartA.points || [], chartB.points || []);
    refreshIcons();
  } catch (error) {
    target.innerHTML = errorCard("Could not compare stocks", error, "compare");
    bindRetry("compare", () => runCompare(event));
  }
}

function flattenCompare(data, a, b) {
  const rows = [];
  ["valuation_comparison", "growth_comparison", "profitability_comparison", "balance_sheet_comparison"].forEach((group) => {
    Object.entries(data[group] || {}).forEach(([metric, values]) => {
      rows.push({ metric: metric.replaceAll("_", " "), a: formatCompareValue(metric, values[a]), b: formatCompareValue(metric, values[b]) });
    });
  });
  if (data.sentiment_comparison) rows.push({ metric: "sentiment", a: data.sentiment_comparison[a] || "—", b: data.sentiment_comparison[b] || "—" });
  return rows;
}

function formatCompareValue(metric, value) {
  if (metric.includes("growth") || metric.includes("margin") || metric === "roe") return fmtPct(value, true);
  return fmtNum(value);
}

function drawCompareChart(a, b, pointsA, pointsB) {
  if (state.compareChart) state.compareChart.destroy();
  const labels = pointsA.map((point) => String(point.date).slice(0, 10));
  state.compareChart = new Chart(document.getElementById("compare-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: a, data: pointsA.map((point) => point.close), borderColor: "#20b2aa", pointRadius: 0, tension: 0.3 },
        { label: b, data: pointsB.map((point) => point.close), borderColor: "#f59e0b", pointRadius: 0, tension: 0.3 },
      ],
    },
    options: chartOptions("price", "volume"),
  });
}

async function renderAdmin() {
  app(`
    <section class="view">
      <div class="view-header">
        <div>
          <h1 class="view-title">Admin Panel</h1>
          <div class="view-subtitle">Local/demo observability for providers, jobs, and DeepSeek usage.</div>
        </div>
      </div>
      <div id="admin-content">${skeleton(4, 180)}</div>
    </section>
  `);
  await loadAdmin();
  state.adminRefresh = setInterval(loadAdmin, 30000);
}

async function loadAdmin() {
  const target = document.getElementById("admin-content");
  if (!target) return;
  try {
    const [status, providers, usage] = await Promise.all([
      api("/api/admin/status"),
      api("/api/health/providers"),
      api("/api/admin/llm-usage"),
    ]);
    const statusData = getData(status);
    const usageData = getData(usage);
    target.innerHTML = `
      <div class="grid-3">
        <div class="kpi-card"><div class="kpi-label">Cache backend</div><div class="kpi-value">${escapeHtml(statusData.cache_backend || providers.cache_backend || "—")}</div></div>
        <div class="kpi-card"><div class="kpi-label">Thread pool</div><div class="kpi-value">${escapeHtml(statusData.thread_pool_max_workers || "—")}</div></div>
        <div class="kpi-card"><div class="kpi-label">LLM calls</div><div class="kpi-value">${fmtNum(usageData.summary?.total_calls || 0, 0)}</div></div>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="panel-header"><div class="panel-title"><i data-lucide="plug-zap"></i>Provider Status</div></div>
        <div class="panel-body"><div class="chips">${providerBadges(providers)}</div>${warningList(providers.warnings)}</div>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="panel-header"><div class="panel-title"><i data-lucide="cpu"></i>DeepSeek Usage</div></div>
        <div class="panel-body">
          <table class="data-table">
            <thead><tr><th>Model</th><th>Agent</th><th>Ticker</th><th>Tokens</th><th>Status</th></tr></thead>
            <tbody>${(usageData.usage || []).slice(0, 12).map((row) => `
              <tr><td>${escapeHtml(row.model)}</td><td>${escapeHtml(row.agent_name || "—")}</td><td>${escapeHtml(row.ticker || "—")}</td><td>${fmtNum(row.total_tokens || 0, 0)}</td><td>${row.success ? "ok" : "failed"}</td></tr>
            `).join("")}</tbody>
          </table>
        </div>
      </div>
    `;
    refreshIcons();
  } catch (error) {
    target.innerHTML = errorCard("Could not load admin data", error, "admin");
    bindRetry("admin", loadAdmin);
  }
}

function providerBadges(providers) {
  return Object.entries(providers)
    .filter(([key, value]) => key.endsWith("_status") || key.endsWith("_configured") || key.endsWith("_available"))
    .slice(0, 36)
    .map(([key, value]) => {
      const display = typeof value === "object" && value !== null ? (value.status || value.backend || JSON.stringify(value)) : value;
      const good = display === true || display === "available" || display === "ok" || display === "configured";
      const bad = display === false || display === "failed";
      return `<span class="badge ${good ? "positive" : bad ? "negative" : ""}">${escapeHtml(key.replaceAll("_", " "))}: ${escapeHtml(display)}</span>`;
    }).join("");
}

function bindRetry(name, fn) {
  document.querySelector(`[data-retry="${name}"]`)?.addEventListener("click", fn);
}
