# Loop Stop — Email Sequence (3)

**Trigger:** Landing signup (“install tips”) or Gumroad/GitHub download with email.  
**Goal:** Download → Integrate → Impact aha.  
**Tone:** Direct. No AI clichés. Label SIMULATED / estimate.

---

## Email 1 — Day 0: Get to Demo

**Subject:** Loop Stop on localhost in one install

**Preview:** Demo is SIMULATED. Live path next.

**Body:**

You asked for install tips for Loop Stop — Coding Agent Token Guard.

1. Unpack the zip (GitHub or Gumroad).  
2. Run `./install.sh` (or `./run.sh` if deps are already there).  
3. Open http://127.0.0.1:8788/  
4. Click **Try Demo mode** — FakeAgent sticky sessions, **SIMULATED**, $0 API.

You should see estimated waste drop on the Impact view (Demo labeled). That is the aha we want first.

Claude Code? Keep this thread — Email 2 is the PreToolUse / plugin path.  
Grok / OpenAI-compatible? You will set `base_url` to `http://127.0.0.1:8788/v1`.

— Loop Stop

---

## Email 2 — Day 2: Integrate (beachhead + proxy)

**Subject:** Hook it to Claude Code (or point base_url)

**Preview:** Detector in the tool path. Dashboard for Impact.

**Body:**

Demo done? Wire the real client.

**Claude Code (recommended beachhead)**  
- Install the Loop Stop plugin from your package, or  
- Point PreToolUse at `hooks/pre_tool_use.sh` (see packaging notes in the zip).  
- Keep `./run.sh` running if you want the Impact charts — the hook catches loops; the dashboard shows them.

**Grok / OpenAI-compatible**  
- Export `XAI_API_KEY` or `GROK_API_KEY`  
- Set client `base_url` to `http://127.0.0.1:8788/v1`  
- Health check: `curl -s http://127.0.0.1:8788/health`

Live “tokens avoided” on the dashboard are **estimates** unless the provider returns `usage`. We do not invent dollar savings.

Stuck on Cursor Base URL? v1 does not promise Cursor localhost routing — use Claude Code, CLI, or an SDK that can hit 127.0.0.1.

— Loop Stop

---

## Email 3 — Day 5: Aha check + honesty

**Subject:** Did a sticky loop actually die?

**Preview:** One blocked event beats another screenshot of Demo.

**Body:**

Quick check-in.

Open the Impact dashboard. Do you have:

- ≥1 **live** blocked loop event, or  
- only the **SIMULATED** Demo seed?

If only Demo: pick one real failing task (broken import, flaky bash, file re-read thrash) and run it with the hook or proxy on. Note tool-call count before/after — label your own notes as estimate.

If something blocked a useful retry: raise threshold N or use the override path in the docs — false positives matter more than a pretty chart.

Reply with which client you use (Claude Code / Grok / other). That steers what we document next. Game-dev tooling is later; we are not spending ad budget there yet.

— Loop Stop

---

## Ops notes

- Do not auto-enroll purchased lists.  
- Gumroad receipt can link Email 1 content in-page if ESP is not ready.  
- Sequence is create-demand friendly: measure first, then integrate.  
