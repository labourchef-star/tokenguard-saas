# Marketing funnel — Loop Stop

```
Ad / organic post
    → Public landing (marketing-site/ or app /)
        → Sign up (/signup)
            → Download (/download + zip)
                → Install (./install.sh | ./run.sh)
                    → Integrations (/integrations)
                        → First Demo (simulated)  OR  live session via proxy/hook
                            → Impact dashboard (/app)
```

## Step notes

| Step | Where | Job |
| --- | --- | --- |
| Attention | X / LinkedIn / Reddit / HN (human posts; Postiz drafts ready) | Pattern-interruption hook from ANGLES.md |
| Landing | `marketing-site/` (Netlify/Pages) or app `/` | Sell problem; show simulated 75%; CTA Sign up / Demo |
| Sign up | `/signup` | Local email+password; cookie session |
| Download | `/download` | Zip + install steps; LAN bind note |
| Integrations | `/integrations` | Grok key / Claude hook / OpenAI base_url |
| Activation | `/app?demo=1` or live `/v1` | First Impact number |
| Habit | Dashboard Impact + Sessions | Return when agents run long |

## Activation definition (v0.1)

User has **either**:

1. Seeded Demo and seen ~75% est. waste reduction (labeled simulated), **or**
2. Connected one integration and recorded ≥1 non-demo session with a blocked loop or annotated event.

## Do not (bot)

- Run paid ads
- Publish via Postiz
- Submit Gumroad / GitHub Release / Anthropic directory
