# Acquisition research — Loop Stop retail

**Product:** local OpenAI-compatible proxy + loop-stop middleware + impact dashboard  
**Constraint:** install-once / local-first (continuous hosted COGS fails Money Engine margin gate)  
**Research date:** 2026-10-28 (Pacific/Auckland)  
**Sources:** Claude Code docs (plugins/hooks), Cursor extension help, VS Code Marketplace peers, Gumroad API docs, Homebrew/pipx patterns

---

## Ranked channels (best first) for THIS product

### 1. GitHub Releases + `install.sh` / clone one-liner — **PRIMARY**

**How the user gets it:** Download a release zip, or `git clone … && ./install.sh`, or
`curl | LOOP_STOP_REPO=… bash` once `install.sh` is hosted on the repo.

**Why #1 for Loop Stop**
- Matches the product: local Python FastAPI process + SQLite + browser dashboard
- Zero ongoing COGS after download
- Covers all three clients (Grok API base_url, Claude Code hook path, any OpenAI-compatible SDK)
- No marketplace review queue; ship the same tree we smoke-tested
- Industry-standard for local AI proxies and CLI middleware

**Needs human:** public (or private) GitHub repo, first Release tag + zip, optional homepage blurb

---

### 2. Gumroad digital download — **PRIMARY PAID**

**How the user gets it:** Buy zip on Gumroad → unpack → `./install.sh` → open
`http://127.0.0.1:8788/`.

**Why #2**
- User already has Gumroad seller API (`edit_products`, draft → upload → enable)
- One-time digital good = no hosted margin bleed
- Fast path to charge without building a storefront
- Same artifact as GitHub Releases (zip of `loop-stop-retail/`)

**Needs human:** price, listing copy, cover art, create/publish product (API or dashboard),
attach zip; do **not** auto-publish without explicit approval

---

### 3. Claude Code hooks / plugin marketplace — **STRONG SECONDARY** (Claude Code users)

**How the user gets it:**
- Immediate: paste PreToolUse hook into `~/.claude/settings.json` pointing at
  `hooks/pre_tool_use.sh` (documented in first-run onboarding)
- Better: ship a Claude Code plugin with `hooks/hooks.json`, add a marketplace repo
  (`claude plugin marketplace add` → `claude plugin install`), or submit to Anthropic’s directory

**Why #3 (not #1)**
- Excellent fit for the *detector* half of the product
- Hook alone does not deliver the Impact dashboard (user still runs `./run.sh` for charts)
- Official plugin system exists and is the natural home for PreToolUse middleware
- Does not cover Grok API / generic OpenAI-compatible users by itself

**Needs human:** decide plugin vs settings-only; marketplace repo or Anthropic directory submit

---

## Channels researched but ranked lower

### npm / pip / Homebrew

| Channel | Verdict |
| --- | --- |
| **pip / PyPI** (`pipx install loop-stop`) | Good later. Needs package name, PyPI account, entrypoint console script. Fits local tool; more ceremony than zip+install.sh for v0.1 |
| **npm** | Poor fit — product is Python FastAPI, not a Node CLI |
| **Homebrew tap** | Fine for Mac power users later (`brew install you/tap/loop-stop`); requires PyPI sdist + formula maintenance. Not first-mile |

### Docker / binary / `curl \| bash`

- **Docker:** easy “run” story (`docker run -p 8788:8788 …`) but heavier for a localhost coding-agent sidecar; optional packaging later
- **Binary (PyInstaller/Nuitka):** possible; large artifact; defer
- **`curl \| bash`:** supported by `install.sh` when `LOOP_STOP_REPO` is set — use as the *distribution wrapper* for GitHub, not a separate product

### VS Code / Cursor extension marketplace

- **VS Code / Open VSX:** feasible (peers run local proxies + dashboards from an extension)
- **Cursor:** Open VSX, not Microsoft Marketplace; **localhost Base URL often blocked** by Cursor’s cloud backend → needs public tunnel (privacy tradeoff) or non-Cursor clients
- **Rank:** later. Thin launcher extension wrapping this app is fine after GitHub+Gumroad

### Hosted SaaS proxy

- Rejected for retail v1: continuous COGS fails Money Engine margin gate; product is explicitly local-first

---

## Plain-English recommendation

Ship **GitHub Releases + install.sh** as the free/default acquire path, put the **same zip on Gumroad** for paid, and document the **Claude Code PreToolUse hook** (then a real plugin) for Claude-heavy users. Skip npm and hosted SaaS. Treat VS Code/Cursor marketplace and Homebrew as follow-ons once the zip path converts.

---

## What still needs a human

1. Create/publish GitHub repo + first Release asset  
2. Gumroad listing (price, copy, zip upload, enable) — seller API ready, no auto-publish  
3. Optional: Claude Code plugin marketplace or Anthropic directory submission  
4. Real `XAI_API_KEY` for live (non-demo) proxy testing  
5. Legal/privacy blurb if tunneling for Cursor is ever documented as supported
