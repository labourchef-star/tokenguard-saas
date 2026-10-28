# VS Code / Cursor extension notes

## Feasibility

- **VS Code Marketplace / Open VSX:** possible — extensions already exist that
  start a local OpenAI-compatible proxy and open a loopback dashboard
  (e.g. AI Proxy, Kotro Proxy Engine patterns).
- **Cursor:** uses Open VSX (not Microsoft Marketplace). Publish to Open VSX
  for Cursor’s Extensions panel.
- **Hard limit:** Cursor routes custom OpenAI Base URL through its cloud
  backend, which **rejects localhost / private addresses**. A pure local proxy
  works for VS Code / Continue / Cline / scripts; Cursor needs a public HTTPS
  tunnel (privacy tradeoff) or a non-Cursor client.

## Recommendation

Defer marketplace extension until GitHub + Gumroad acquisition is live.
When built: extension = thin launcher for this Python app + status bar link
to `http://127.0.0.1:8788/`.
