# OneMi

**One config, three devices. AI-first proxy architecture for Clash Verge / ClashMeta / Shadowrocket.**

> **English** | [中文](README_CN.md)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](#changelog)

```
OneMi/
├── OneMi-Windows-ClashVerge.yaml    # Windows + Clash Verge Rev
├── OneMi-S24-ClashMeta.yaml         # Android (Samsung S24) + ClashMeta
├── OneMi-iPhone-YAML.yaml           # iPhone + Shadowrocket (mihomo YAML)
├── OneMi-iPhone-Shadowrocket.conf   # iPhone + Shadowrocket (native .conf)
└── gen_onemi.py                     # Generate all platforms from one source
```

---

## What is OneMi?

OneMi is a **single-config, multi-device AI proxy architecture**. You write the rules once, run a script, and get optimized configs for Windows, Android, and iPhone — all sharing the same 12-group, 154-rule architecture tuned specifically for AI services.

### Why not just use someone else's Clash config?

Most Clash configs treat AI services like any other website — throw them in a generic "proxy" group and hope for the best. OneMi is built from hundreds of hours of real debugging:

- **ChatGPT dead on HK nodes** but works on USA — same exit IP, different routing path
- **Gemini blocked on Luxembourg IPs** — Google rejects certain FranTech ranges
- **Claude returns 403 via curl** but works in browser — Cloudflare Bot Management
- **anytls cold-start 1900ms** first request, 400ms after — needs `lazy: false` warm-up
- **Shadowrocket greedy `KEYWORD,google`** captures Gemini's auxiliary domains → white screen

Full details in [`docs/pitfalls.md`](docs/pitfalls.md).

---

## The 12-Group Architecture

| # | Group | Type | Covers | Why |
|---|-------|------|--------|-----|
| 1 | **Google-AI** | fallback | Gemini, NotebookLM, AI Studio | Google blocks certain IP ranges |
| 2 | **AI-Proxy** | fallback | ChatGPT, Claude, Grok | Some nodes dead for OpenAI even if they work for everything else |
| 3 | **Note-Tools** | url-test | Notion, Obsidian, Craft | Low-stakes |
| 4 | **Dev-AI** | url-test | Cursor, Copilot, Replit | Low-stakes |
| 5 | **CF-Strict** | select | Perplexity, Mistral, Poe | Cloudflare Bot Management — needs manual selection |
| 6 | **Social** | fallback | Telegram, Discord, WhatsApp | High-frequency — needs stability |
| 7 | **Dev-Svc** | fallback | Docker, PyPI, npm, Vercel | High-frequency |
| 8 | **Web3** | fallback | Binance, Coinbase, DeFi | Exchange geo-blocking varies |
| 9 | **Finance** | fallback | Bloomberg, Reuters, NYT | News/finance geo-blocking |
| 10 | **Game-Media** | fallback | Netflix, YouTube, Spotify | Session continuity |
| 11 | **Shopping** | fallback | Amazon, eBay, Zara | E-commerce geo-blocking |
| 12 | **Proxy** | url-test | Everything else | Fallback |

### Why `fallback` instead of `url-test` for AI?

| | `url-test` | `fallback` |
|---|---|---|
| Selects by | Lowest latency to test URL | First available (ordered by priority) |
| Problem | Fast for gstatic ≠ working for OpenAI | Health check uses the **actual service** |
| Behavior | Jumps to "fastest" constantly | Stays until failure |

---

## Quick Start

### Option A: Use OneMi configs directly

```bash
# Clone
git clone https://github.com/MiLab-Bit/clash-ai-proxy.git
cd clash-ai-proxy

# Pick your platform
cp OneMi-Windows-ClashVerge.yaml ~/.config/clash/config.yaml   # Windows
cp OneMi-S24-ClashMeta.yaml /sdcard/ClashMeta/config.yaml       # Android
# iPhone: AirDrop OneMi-iPhone-YAML.yaml → Shadowrocket
```

Replace the `proxies:` section with your own nodes (from your airport subscription).

### Option B: Use the CLI to auto-generate

```bash
pip install clash-ai-proxy

# Test which nodes can reach AI services
clash-ai test --proxy http://127.0.0.1:7897

# Test node stability
clash-ai latency --config ~/.config/clash/config.yaml

# Generate optimized config (auto-excludes dead nodes)
clash-ai generate --config ~/.config/clash/config.yaml --output optimized.yaml
```

---

## What's in the config? (2026 best practices)

### Engine-level optimizations

| Setting | Value | Why |
|---------|-------|-----|
| `tcp-concurrent` | `true` | Parallel TCP racing, auto-selects fastest path |
| `geodata-mode` | `true` | `.dat` format, 40% less memory |
| `keep-alive-interval` | `30` | Reduced keepalive, saves battery |
| `global-client-fingerprint` | `chrome` | Unified TLS fingerprint |
| `find-process-mode` | `off` (mobile) / `strict` (desktop) | Platform-appropriate |

### DNS architecture

| Layer | What it does |
|-------|-------------|
| `enhanced-mode: fake-ip` | No DNS leak for proxied domains |
| `nameserver-policy` by GEOSITE | CN domains → Chinese DoH, AI domains → Google DoH, Apple/MS → Chinese DoH |
| `direct-nameserver` + `follow-policy` | Direct traffic DNS doesn't go through proxy |
| `geosite:category-ads-all → rcode://success` | Ad domains return empty (no "loading spinner") |
| `store-fake-ip: true` | Persist fake-ip across config reloads |
| `cache-algorithm: arc` | Better DNS cache hit rate |

### TUN configuration

| Platform | Stack | MTU | Notes |
|----------|-------|-----|-------|
| Android | `mixed` (TCP=system + UDP=gvisor) | `1500` | Best ROM compatibility |
| Windows | `gvisor` | default | No admin needed |
| iOS | `system` | default | iOS limitation |

DNS hijack: `any:53` + `tcp://any:53` (some apps use TCP DNS).

### Sniffer — stable mode

```yaml
sniffer:
  parse-pure-ip: false          # Don't sniff raw IPs (breaks banking apps)
  override-destination: false   # Don't override (breaks cert-pinned apps)
  skip-domain:                  # Skip these entirely
    - "+.icbc.com.cn"           # ICBC
    - "+.apple.com"             # Apple cert-pinned
    - "+.icloud.com"            # iCloud cert-pinned
```

### Rules — proper ordering

```
Private networks → AI GEOSITE → AI static assets → Apple/MS direct →
CN domains → CN IP → Ad-block → MATCH
```

- **No `DOMAIN-KEYWORD`** for AI services — too broad (`openai.example-blog.com` would match)
- **AI static domains** explicitly routed (oaistatic, anthropicusercontent, etc.) — fixes "chat works but images/CSS don't load"
- **Apple/Microsoft → DIRECT** for China App Store/iCloud/Office
- **`GEOIP,CN,no-resolve`** — don't reverse-resolve under fake-ip

### MRS native rulesets

Uses mihomo's `.mrs` format (binary, faster parsing, smaller) alongside blackmatrix7 YAML for granular AI service coverage.

### Security

- `skip-cert-verify: false` on all nodes (anytls doesn't verify TLS anyway)
- Random `secret` (not dictionary password)
- `allow-lan: false` by default

### Battery-friendly (mobile)

- All groups: `lazy: true` + `interval: 300` (was 120-180s with lazy:false)
- `find-process-mode: off` on mobile (no procfs overhead)

---

## Comparison

| Feature | [Loyalsoldier](https://github.com/Loyalsoldier/clash-rules) (18k★) | [blackmatrix7](https://github.com/blackmatrix7/ios_rule_script) (20k★) | **OneMi** |
|---------|--------|--------|--------|
| What it gives you | Domain rule lists | Per-service rule files | **Full architecture + configs + CLI** |
| AI-specific routing | ❌ | Rule files only | **✅ Per-service health checks** |
| Multi-device sync | ❌ | ❌ | **✅ One source → 3 platforms** |
| Dead node detection | ❌ | ❌ | **✅ CLI tests each node** |
| Latency stability test | ❌ | ❌ | **✅ Jitter measurement** |
| Auto-exclude bad nodes | ❌ | ❌ | **✅ Generator skips them** |
| 2026 mihomo features | ❌ | ❌ | **✅ MRS / GEOSITE DNS / store-fake-ip** |

> **These projects are complementary.** Rule projects manage *domains*, OneMi manages *nodes + architecture*. Use them together.

---

## CLI Reference

```bash
# Test service reachability
clash-ai test --proxy http://127.0.0.1:7897

# Test node latency (5 samples, jitter detection)
clash-ai latency --config config.yaml --samples 5

# Generate config (Clash YAML or Shadowrocket conf)
clash-ai generate --config config.yaml --output optimized.yaml
clash-ai generate --config config.yaml --format shadowrocket --output optimized.conf

# Full pipeline: test + classify + generate
clash-ai full --config config.yaml --proxy http://127.0.0.1:7897
```

---

## Supported Services

| Category | Services |
|----------|----------|
| **AI** | ChatGPT, Claude, Gemini, Grok, Perplexity, Cursor, Copilot, Cohere, Mistral, Poe, HuggingFace |
| **Streaming** | Netflix, YouTube, Disney+, HBO, Prime Video, Spotify, Crunchyroll |
| **Social** | Telegram, Discord, Twitter/X, WhatsApp, Instagram, Reddit |
| **Dev** | GitHub, Docker, PyPI, npm, Vercel, Supabase |
| **Web3** | Binance, Coinbase, OKX, MetaMask, Etherscan |
| **Direct** | Apple, iCloud, Microsoft, Samsung, Steam CDN, Tailscale |

---

## Who is this for?

- ✅ You use **Clash/mihomo/ClashMeta/Shadowrocket** with multiple nodes
- ✅ You access **AI services** (ChatGPT, Claude, Gemini) and need them to **just work**
- ✅ You have **multiple devices** (PC + phone) and want the same config
- ✅ You want **2026 best practices** (MRS rulesets, GEOSITE DNS, fake-ip persistence)

Not for you if: you only use one node, or you don't access geo-restricted services.

---

## Generating from source

```bash
# Edit OneMi-S24-ClashMeta.yaml (the master config)
# Then regenerate all platforms:
python gen_onemi.py
# → OneMi-Windows-ClashVerge.yaml
# → OneMi-iPhone-YAML.yaml
# → OneMi-iPhone-Shadowrocket.conf
```

---

## Contributing

Contributions welcome! Especially:

- 🌍 **New service definitions** — add services from your region
- 🐛 **Dead-node patterns** — report which airports have which dead nodes for which services
- 🔧 **New proxy clients** — add support for Surge, Quantumult X, sing-box
- 📝 **Pitfall documentation** — found a new gotcha? Add it to `docs/pitfalls.md`

---

## Changelog

### v2.0.0 — OneMi Brand (2026-10-05)

**Breaking:** Unified brand name "OneMi", internal version 1.0. Multi-device generation from single source.

| Change | Impact |
|--------|--------|
| **OneMi brand** | All configs unified under OneMi, file format: `OneMi-{Device}-{App}.{ext}` |
| **gen_onemi.py** | Generate Windows/Android/iPhone configs from one master YAML |
| **MRS native rulesets** | `.mrs` format (geosite-ai/cn/ads + geoip-cn) — faster parsing, smaller size |
| **DNS by GEOSITE** | `nameserver-policy` uses `geosite:cn` / `geosite:google` / etc. instead of hand-written domain lists |
| **Ad-block silent** | `geosite:category-ads-all → rcode://success` in DNS (no loading spinner) |
| **AI static assets** | oaistatic, anthropicusercontent, files.chatgpt, cdn.anthropic, static.claude — fixes "chat works but images don't load" |
| **Removed DOMAIN-KEYWORD** | All keyword rules deleted — too broad, GEOSITE+DOMAIN-SUFFIX is precise |
| **store-fake-ip: true** | Persist fake-ip across reloads — AI long connections don't re-handshake |
| **cache-algorithm: arc** | Better DNS cache hit rate than default LRU |
| **direct-nameserver** | Direct traffic gets its own DNS, doesn't pollute fake-ip |
| **Battery-friendly** | All groups `lazy: true` + `interval: 300` — less background testing on mobile |
| **Private network rules** | Head of rules: 127.x/10.x/172.16.x/192.168.x/100.64.x → DIRECT (NAS/printers/hotspot) |
| **Apple/Microsoft/Samsung completed** | 19 new rules: App Store, OCSP, OneDrive, Samsung DNS, Samsung push |
| **Ad REJECT repositioned** | Moved to MATCH-1 (DNS layer already silent, rules layer as backup) |
| **Rule ordering finalized** | Private → AI → Apple → CN domain → CN IP → Ads → MATCH |
| **Strong secret** | Random 32-char token instead of dictionary password |

### v1.3.0 (2026-10-05)

Security & stability refinements: skip-cert-verify default false, sniffer stable mode, TUN enabled, GEOSITE ad-block, Apple/Microsoft/Cloudflare/Tailscale/Steam rules.

### v1.2.0 (2026-10-05)

Engine-level optimizations: tcp-concurrent, sniffer, geodata-mode, GeoSite rules, nameserver-policy, max-failed-times, keep-alive-interval, global-client-fingerprint.

### v1.1.0 (2026-10-05)

Architecture upgrades: lazy:false, fake-ip-filter AI domains, rule-providers, node priority sorting, IPv6 disabled, DoH fallback, CF-Strict group.

### v1.0.0

Initial release. CLI with test/latency/generate/full commands. 11-layer architecture. Clash + Shadowrocket support.

---

## License

[MIT](LICENSE)
