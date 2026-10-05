# Configuration Templates

Battle-tested templates from real airport debugging. Use these as a starting point and customize with `clash-ai generate`.

## Files

| File | Platform | Description |
|------|----------|-------------|
| [`clash-verge-template.yaml`](clash-verge-template.yaml) | Clash Verge / mihomo | 11-layer architecture with rule-providers, fake-ip-filter, lazy connections |
| [`shadowrocket-template.conf`](shadowrocket-template.conf) | Shadowrocket (iOS) | Same architecture adapted for Shadowrocket syntax |

## Usage

### Option A: Use template directly

1. Copy the template to your Clash config directory
2. Replace the `proxies:` section with your actual nodes (from your subscription)
3. Update proxy group node lists to match your node names

### Option B: Generate from your subscription (recommended)

```bash
# Auto-generates config with your nodes, excluding dead/unstable ones
clash-ai full --config your-subscription.yaml --proxy http://127.0.0.1:7897
```

## Template Highlights

These templates incorporate all optimizations from [`docs/pitfalls.md`](../docs/pitfalls.md):

- **`lazy: false`** — connections stay warm, no cold-start penalty
- **`fake-ip-filter`** — AI domains bypass fake-ip (prevents detection)
- **`rule-providers`** — blackmatrix7 remote rulesets, daily auto-update
- **Priority sorting** — `-02` nodes first (proven lower jitter in practice)
- **IPv6 disabled** — prevents leaks on airports without IPv6 support
- **DoH fallback** — `1.1.1.1/dns-query` for tamper-resistant DNS
- **Greedy keyword fix** — service-specific rules before `DOMAIN-KEYWORD,google`
