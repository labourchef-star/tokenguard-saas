/* TokenGuard SaaS dashboard + onboarding */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let onboardingState = { completed: false, client: null, demo_mode: false, step: "welcome" };
let selectedClient = null;
let creds = { base_url: "https://HOST/v1", api_key: "tg_…" };

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3200);
}

function fmt(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString();
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadCredentials() {
  try {
    const r = await fetch("/api/auth/me");
    if (r.status === 401) {
      $("#cred-banner")?.classList.add("hidden");
      return null;
    }
    const me = await r.json();
    creds = me.credentials || {
      base_url: `${location.origin}/v1`,
      api_key: me.api_key || "tg_…",
    };
    if ($("#dash-base")) $("#dash-base").textContent = creds.base_url;
    if ($("#dash-key")) $("#dash-key").textContent = creds.api_key;
    $("#cred-banner")?.classList.remove("hidden");
    return me;
  } catch (_) {
    return null;
  }
}

const STEPS = ["welcome", "client", "config"];

function paintSteps(current) {
  const idx = STEPS.indexOf(current);
  $("#ob-steps").innerHTML = STEPS.map((_, i) => {
    let cls = "";
    if (i < idx) cls = "done";
    else if (i === idx) cls = "on";
    return `<span class="${cls}"></span>`;
  }).join("");
}

function showObStep(name) {
  onboardingState.step = name;
  paintSteps(name);
  $$(".ob-panel").forEach((p) => p.classList.toggle("hidden", p.dataset.step !== name));
  if (name === "config") renderConfig();
}

function showOnboarding() {
  $("#onboarding").classList.remove("hidden");
  $("#app").classList.add("hidden");
  showObStep(onboardingState.step || "welcome");
}

function showApp() {
  $("#onboarding").classList.add("hidden");
  $("#app").classList.remove("hidden");
  loadCredentials();
  loadImpact();
}

async function persistOnboarding(patch) {
  const r = await fetch("/api/onboarding", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  onboardingState = await r.json();
  return onboardingState;
}

function configCopy(client) {
  const base = creds.base_url || `${location.origin}/v1`;
  const key = creds.api_key || "tg_YOUR_KEY";
  if (client === "claude_code") {
    return {
      title: "Claude Code → hosted TokenGuard",
      html: `
        <p>Point OpenAI-compatible settings at the <strong>hosted</strong> URL (not localhost):</p>
        <div class="config-box">
          <pre>export OPENAI_BASE_URL="${base}"
export OPENAI_API_KEY="${key}"</pre>
          <p style="margin:10px 0 0" class="muted">
            Optional: paste an upstream xAI/OpenAI key on
            <a href="/integrations">Integrations</a> (encrypted). Demo works without it.
          </p>
        </div>`,
    };
  }
  if (client === "grok_api") {
    return {
      title: "Grok / xAI via TokenGuard",
      html: `
        <ol class="muted">
          <li>Copy your base_url and tg_ key below (or from the dashboard banner).</li>
          <li>Optional: paste your xAI key on <a href="/integrations">Integrations</a> (BYOK, encrypted).</li>
          <li>Or forward an xAI key as Authorization Bearer (non-tg_ keys are passed upstream).</li>
        </ol>
        <div class="config-box">
          Python SDK:
          <pre>from openai import OpenAI
client = OpenAI(
    base_url="${base}",
    api_key="${key}",
)
r = client.chat.completions.create(
    model="grok-4.7",
    messages=[{"role":"user","content":"hi"}],
)</pre>
        </div>`,
    };
  }
  return {
    title: "OpenAI-compatible client",
    html: `
      <ol class="muted">
        <li>Set client <span class="mono">base_url</span> to
          <span class="mono">${escapeHtml(base)}</span>.</li>
        <li>Set API key to <span class="mono">${escapeHtml(key)}</span>.</li>
        <li>Use Demo mode for a simulated before/after without any upstream key.</li>
      </ol>
      <div class="config-box">
        Hosted SaaS — no localhost tunnel required for Continue / Cline / scripts.
      </div>`,
  };
}

function renderConfig() {
  const c = selectedClient || onboardingState.client || "openai_compatible";
  const info = configCopy(c);
  $("#config-body").innerHTML = `<h2 style="font-size:1.05rem;margin:0 0 8px;">${info.title}</h2>${info.html}
    <p class="muted" style="margin-top:14px;">
      No upstream key yet? Click <strong>Try Demo mode</strong> — simulated sticky sessions
      (~75% est. waste reduction). Demo = simulated.
    </p>`;
}

$("#ob-start").addEventListener("click", () => {
  persistOnboarding({ step: "client" });
  showObStep("client");
});

$$(".client-card").forEach((card) => {
  card.addEventListener("click", async () => {
    selectedClient = card.dataset.client;
    $$(".client-card").forEach((c) => c.classList.toggle("selected", c === card));
    await persistOnboarding({ client: selectedClient, step: "config" });
    showObStep("config");
  });
});

$("#ob-back-client").addEventListener("click", () => {
  persistOnboarding({ step: "client" });
  showObStep("client");
});

$("#ob-try-demo").addEventListener("click", async () => {
  const btn = $("#ob-try-demo");
  btn.disabled = true;
  btn.textContent = "Seeding…";
  try {
    const r = await fetch("/api/demo/seed?replay=true", { method: "POST" });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "seed failed");
    await persistOnboarding({ completed: true, demo_mode: true, step: "done" });
    toast(`Demo seeded: ${data.sessions_created?.length || 0} sessions (simulated)`);
    showApp();
  } catch (e) {
    toast(String(e.message || e));
  } finally {
    btn.disabled = false;
    btn.textContent = "Try Demo mode";
  }
});

$("#ob-finish").addEventListener("click", async () => {
  await persistOnboarding({ completed: true, step: "done" });
  showApp();
});

$("#btn-redo-onboard").addEventListener("click", async () => {
  await persistOnboarding({ completed: false, step: "welcome" });
  showOnboarding();
});

function showView(name) {
  ["impact", "sessions", "settings"].forEach((v) => {
    $(`#view-${v}`).classList.toggle("hidden", v !== name);
  });
  $$("nav button[data-view]").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === name);
  });
  if (name === "sessions") {
    $("#session-detail-panel").classList.add("hidden");
    $("#sessions-list").parentElement.classList.remove("hidden");
  }
}

$$("nav button[data-view]").forEach((b) => {
  b.addEventListener("click", () => {
    showView(b.dataset.view);
    if (b.dataset.view === "impact") loadImpact();
    if (b.dataset.view === "sessions") loadSessions();
    if (b.dataset.view === "settings") loadSettings();
  });
});

async function loadImpact() {
  const data = await fetch("/api/impact").then((r) => r.json());
  const metrics = [
    { label: "Tokens used", value: data.tokens_used, hint: "In + out across sessions" },
    { label: "Tokens saved (est.)", value: data.tokens_saved_est, hint: "Avoided by TokenGuard", badge: "est" },
    { label: "% waste reduction (est.)", value: `${data.pct_waste_reduction_est}%`, hint: "saved / (used + saved)" },
    { label: "Sessions counted", value: data.sessions_counted, hint: `${fmt(data.loops_blocked)} loops blocked` },
  ];
  $("#impact-metrics").innerHTML = metrics
    .map(
      (m) => `
    <div class="metric">
      <div class="label">${m.label}</div>
      <div class="value">${typeof m.value === "number" ? fmt(m.value) : m.value}</div>
      <div class="hint">${m.hint}${m.badge === "est" ? ' · <span class="badge est">estimate</span>' : ""}</div>
    </div>`
    )
    .join("");
  $("#cmp-baseline").textContent = fmt(data.baseline_tool_calls);
  $("#cmp-stop").textContent = fmt(data.with_stop_tool_calls);
  $("#impact-honesty").textContent = "honesty: estimates labeled";

  const used = data.tokens_used || 0;
  const saved = data.tokens_saved_est || 0;
  const max = Math.max(used, saved, 1);
  $("#impact-chart").innerHTML = `
    <div class="bar" style="height:${Math.max(8, (used / max) * 120)}px"><span>used</span></div>
    <div class="bar saved" style="height:${Math.max(8, (saved / max) * 120)}px"><span>saved est.</span></div>
  `;

  const recent = data.recent_sessions || [];
  if (!recent.length) {
    $("#impact-recent").innerHTML =
      '<span class="muted">No sessions yet. Click <strong>Demo mode</strong> to seed simulated sticky loops.</span>';
    return;
  }
  $("#impact-recent").innerHTML = `<table>
    <thead><tr><th>Title</th><th>Mode</th><th>Used</th><th>Saved est.</th><th>Blocked</th><th>Source</th></tr></thead>
    <tbody>
      ${recent
        .map(
          (s) => `<tr class="clickable" data-id="${s.id}">
        <td>${escapeHtml(s.title || s.id)}</td>
        <td><span class="badge ${s.mode === "demo" ? "demo" : ""}">${s.mode}</span></td>
        <td>${fmt((s.tokens_in || 0) + (s.tokens_out || 0))}</td>
        <td>${fmt(s.tokens_avoided_est)}</td>
        <td>${fmt(s.loop_events_blocked)}</td>
        <td><span class="badge ${s.tokens_source === "provider" ? "provider" : "est"}">${s.tokens_source}</span></td>
      </tr>`
        )
        .join("")}
    </tbody></table>`;
  $$("#impact-recent tr.clickable").forEach((tr) => {
    tr.addEventListener("click", () => {
      showView("sessions");
      openSession(tr.dataset.id);
    });
  });
}

async function loadSessions() {
  const data = await fetch("/api/sessions").then((r) => r.json());
  const sessions = data.sessions || [];
  if (!sessions.length) {
    $("#sessions-list").innerHTML = '<span class="muted">No sessions. Run Demo mode or proxy a chat.</span>';
    return;
  }
  $("#sessions-list").innerHTML = `<table>
    <thead><tr><th>When</th><th>Title</th><th>Mode</th><th>Tools</th><th>Blocked</th><th>Tokens</th></tr></thead>
    <tbody>
      ${sessions
        .map((s) => {
          const when = s.created_at ? new Date(s.created_at * 1000).toLocaleString() : "—";
          return `<tr class="clickable" data-id="${s.id}">
            <td class="muted">${when}</td>
            <td>${escapeHtml(s.title || s.id)}</td>
            <td>${s.mode}</td>
            <td>${fmt(s.tool_call_count)}</td>
            <td>${fmt(s.loop_events_blocked)}</td>
            <td>${fmt((s.tokens_in || 0) + (s.tokens_out || 0))}
              <span class="badge ${s.tokens_source === "provider" ? "provider" : "est"}">${s.tokens_source}</span></td>
          </tr>`;
        })
        .join("")}
    </tbody></table>`;
  $$("#sessions-list tr.clickable").forEach((tr) => {
    tr.addEventListener("click", () => openSession(tr.dataset.id));
  });
}

async function openSession(id) {
  const s = await fetch(`/api/sessions/${id}`).then((r) => r.json());
  $("#sessions-list").parentElement.classList.add("hidden");
  $("#session-detail-panel").classList.remove("hidden");
  $("#session-detail-title").textContent = s.title || s.id;
  $("#session-detail-meta").innerHTML = `
    <span class="mono">${s.id}</span> · ${s.mode} · model ${escapeHtml(s.model || "—")} ·
    tools ${fmt(s.tool_call_count)} · blocked ${fmt(s.loop_events_blocked)} ·
    used ${fmt((s.tokens_in || 0) + (s.tokens_out || 0))}
    <span class="badge ${s.tokens_source === "provider" ? "provider" : "est"}">${s.tokens_source}</span>
    · saved est. ${fmt(s.tokens_avoided_est)}
    ${s.baseline_tool_calls != null ? ` · before ${fmt(s.baseline_tool_calls)} → with-stop ${fmt(s.with_stop_tool_calls)}` : ""}
  `;
  const events = s.events || [];
  if (!events.length) {
    $("#session-timeline").innerHTML = '<li class="muted">No events</li>';
    return;
  }
  $("#session-timeline").innerHTML = events
    .map((e) => {
      const blocked = e.kind === "tool_blocked" || e.allowed === false;
      const when = e.ts ? new Date(e.ts * 1000).toLocaleTimeString() : "";
      const args = e.args ? `<div class="mono muted">${escapeHtml(JSON.stringify(e.args))}</div>` : "";
      const detail = e.detail ? `<div class="muted">${escapeHtml(e.detail)}</div>` : "";
      return `<li class="${blocked ? "blocked" : ""}">
        <div><span class="kind">${escapeHtml(e.kind)}</span>
          ${e.tool ? ` · <span class="mono">${escapeHtml(e.tool)}</span>` : ""}
          <span class="muted"> ${when}</span>
          ${blocked ? ' <span class="badge" style="background:#3a1020;color:#f31260;">blocked</span>' : ""}
        </div>
        ${args}${detail}
      </li>`;
    })
    .join("");
}

$("#btn-back-sessions").addEventListener("click", () => {
  $("#session-detail-panel").classList.add("hidden");
  $("#sessions-list").parentElement.classList.remove("hidden");
  loadSessions();
});

async function loadSettings() {
  const s = await fetch("/api/settings").then((r) => r.json());
  $("#upstream").value = s.upstream_base_url || "";
  $("#model").value = s.default_model || "";
  $("#loop_n").value = s.loop_n;
  $("#block_loops").value = String(!!s.block_loops);
  $("#key-status").textContent = s.api_key_configured
    ? `configured via ${s.api_key_source}`
    : "not set (per-user BYOK / Demo / forward Bearer still work)";
  if (s.credentials) {
    creds = s.credentials;
    if ($("#dash-base")) $("#dash-base").textContent = creds.base_url;
    if ($("#dash-key")) $("#dash-key").textContent = creds.api_key;
  }
}

$("#btn-save-settings").addEventListener("click", async () => {
  const body = {
    upstream_base_url: $("#upstream").value.trim(),
    default_model: $("#model").value.trim(),
    loop_n: Number($("#loop_n").value),
    block_loops: $("#block_loops").value === "true",
  };
  const r = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    toast("Failed to save settings");
    return;
  }
  toast("Settings saved");
  loadSettings();
});

$("#btn-demo").addEventListener("click", async () => {
  const btn = $("#btn-demo");
  btn.disabled = true;
  btn.textContent = "Seeding…";
  try {
    const r = await fetch("/api/demo/seed?replay=true", { method: "POST" });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "seed failed");
    toast(`Demo seeded: ${data.sessions_created?.length || 0} sessions (simulated)`);
    showView("impact");
    await loadImpact();
  } catch (e) {
    toast(String(e.message || e));
  } finally {
    btn.disabled = false;
    btn.textContent = "Demo mode";
  }
});

(async function boot() {
  const params = new URLSearchParams(location.search);
  const wantDemo = params.get("demo") === "1";
  await loadCredentials();
  try {
    onboardingState = await fetch("/api/onboarding").then((r) => r.json());
  } catch (_) {
    onboardingState = { completed: false, step: "welcome" };
  }
  selectedClient = onboardingState.client || null;
  if (wantDemo) {
    showApp();
    try {
      const r = await fetch("/api/demo/seed?replay=true", { method: "POST" });
      const data = await r.json();
      if (r.ok) {
        toast(`Demo seeded: ${data.sessions_created?.length || 0} sessions (simulated)`);
        await persistOnboarding({ completed: true, demo_mode: true, step: "done" });
        await loadImpact();
      } else {
        toast(data.detail || "Demo seed failed");
      }
    } catch (e) {
      toast(String(e.message || e));
    }
    return;
  }
  // Signed-in users with credentials skip wizard unless first visit
  const me = await loadCredentials();
  if (me && (onboardingState.completed || params.get("skip_onboard") === "1" || me.api_key)) {
    // first login after signup: show app with credentials banner
    if (!onboardingState.completed) await persistOnboarding({ completed: true, step: "done" });
    showApp();
  } else if (onboardingState.completed || params.get("skip_onboard") === "1") {
    showApp();
  } else if (me) {
    showApp();
  } else {
    showOnboarding();
  }
})();
