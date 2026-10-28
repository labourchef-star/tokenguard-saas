# Email 3-touch sequence (markdown drafts)

From your own ESP later. Do **not** send from the bot unless the user explicitly approves recipients + body.

---

## Touch 1 — Day 0 (after signup)

**Subject:** Your Loop Stop download + a 2-minute demo

Hi {{name}},

Thanks for signing up. Loop Stop runs on your machine — local proxy, local dashboard.

1. Download the zip (link in the app: /download)  
2. Run `./install.sh`  
3. Click **Demo mode** for a **simulated** sticky-loop session (~75% est. waste reduction, labeled estimate)

Then open Integrations if you use Claude Code or Grok.

— Loop Stop

---

## Touch 2 — Day 2

**Subject:** Did the agent re-read the same file again?

If Demo looked familiar, wire one client:

- Claude Code → PreToolUse hook on Integrations  
- Grok → paste key, set base_url to `http://127.0.0.1:8788/v1`

Live savings stay labeled **estimate** unless your provider returns usage.

---

## Touch 3 — Day 5

**Subject:** Before your next overnight agent run

Unattended sessions amplify sticky loops. Two checks:

1. Impact dashboard — any blocked events yet?  
2. Loop threshold N in Settings (default 3)

Still on the fence? Re-run Demo — it’s simulated and free.
