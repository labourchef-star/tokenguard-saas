# GitHub Releases

**Do not auto-publish.** Human creates the repo + Release.

## Artifact

```
dist/loop-stop-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip
```

Built with:

```bash
./packaging/build_release.sh
```

## Suggested Release body

```
Loop Stop — Coding Agent Token Guard v0.1.0 (initial retail)

Install:
  unzip loop-stop-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip
  cd loop-stop-CODING-AGENT-TOKEN-GUARD-v0.1.0
  ./install.sh
Dashboard: http://127.0.0.1:8788/

Claude Code plugin (local marketplace):
  claude plugin marketplace add /path/to/extracted/folder
  claude plugin install loop-stop@loop-stop-marketplace
```

## curl | bash (after repo exists)

```bash
LOOP_STOP_REPO=https://github.com/YOU/loop-stop.git \
  bash -c 'git clone "$LOOP_STOP_REPO" ~/loop-stop && ~/loop-stop/install.sh'
```
