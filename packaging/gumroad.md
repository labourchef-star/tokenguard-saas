# Gumroad listing notes

## Artifact

Built by `packaging/build_release.sh`:

```
/workspace/grok-dev/loop-stop-retail/dist/tokenguard-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip
```

## Product shape

- **Type:** digital download (one-time), not membership / hosted SaaS
- **Name:** TokenGuard — Coding Agent Token Guard
- **Permalink:** tokenguard (if available)
- **Price:** $19.00 (1900 cents)
- **File:** the zip above
- **Receipt path:** unpack → `./install.sh` → `http://127.0.0.1:8788/`

## API flow

1. `POST /v2/files/presign` → PUT bytes → `POST /v2/files/complete`
2. `POST /v2/products` with `native_type=digital`, `files[][url]`, `draft=false` or enable after
3. Delete leftover probe products named "TokenGuard probe"
