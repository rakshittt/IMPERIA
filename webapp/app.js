async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = text;
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(payload)}`);
  }
  return payload;
}

function addBubble(role, text) {
  const log = document.getElementById("chat-log");
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  if (role === "assistant") {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderMarkdown(input) {
  let html = escapeHtml(input || "");
  html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.*)$/gm, "<h1>$1</h1>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^- (.*)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  html = html.replace(/<p>\s*<\/p>/g, "");
  html = html.replace(/<\/ul><ul>/g, "");
  return html;
}

function extractTicker(text) {
  const matches = text.toUpperCase().match(/\b[A-Z]{1,5}\b/g);
  if (!matches) return "AAPL";
  const stop = new Set(["WHAT", "WHY", "HOW", "THE", "AND", "FOR", "WITH", "TODAY", "THIS", "THAT"]);
  return matches.find((token) => !stop.has(token)) || "AAPL";
}

function toNaturalText(payload) {
  if (!payload || typeof payload !== "object") return "I could not understand the backend response.";
  if (typeof payload.answer === "string" && payload.answer.trim()) return payload.answer.trim();
  if (payload.data && typeof payload.data.answer === "string" && payload.data.answer.trim()) return payload.data.answer.trim();
  if (payload.data && typeof payload.data.summary === "string" && payload.data.summary.trim()) return payload.data.summary.trim();
  if (typeof payload.summary === "string" && payload.summary.trim()) return payload.summary.trim();
  if (payload.data && typeof payload.data.what_happened_today === "string" && payload.data.what_happened_today.trim()) {
    return payload.data.what_happened_today.trim();
  }
  if (Array.isArray(payload.results) && payload.results.length) {
    const top = payload.results[0];
    if (top?.ticker && top?.name) {
      return `I found ${payload.results.length} matches. Top match is ${top.ticker} (${top.name}).`;
    }
  }
  return "I received data from backend, but I could not build a clean sentence from it.";
}

async function handleNaturalQuery(userText) {
  const ticker = extractTicker(userText);
  const result = await api("/api/agent/analyst", {
    method: "POST",
    body: JSON.stringify({ ticker, query: userText, window: "today" }),
  });
  if (typeof result.analyst_response === "string" && result.analyst_response.trim()) {
    return result.analyst_response.trim();
  }
  return toNaturalText(result);
}

async function submitMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  addBubble("user", message);

  try {
    addBubble("system", "Thinking...");
    const answer = await handleNaturalQuery(message);
    const log = document.getElementById("chat-log");
    const pending = log.querySelector(".system:last-child");
    if (pending && pending.textContent === "Thinking...") pending.remove();
    addBubble("assistant", answer);
  } catch (err) {
    const log = document.getElementById("chat-log");
    const pending = log.querySelector(".system:last-child");
    if (pending && pending.textContent === "Thinking...") pending.remove();
    addBubble("assistant", `I hit an error while calling backend: ${String(err.message || err)}`);
  }
}

document.getElementById("btn-send").addEventListener("click", submitMessage);
document.getElementById("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitMessage();
  }
});

addBubble("assistant", "Welcome to lunk ka devta. Ask your stock question and I will reply in natural language.");
