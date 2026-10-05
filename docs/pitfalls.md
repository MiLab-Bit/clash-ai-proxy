# Pitfalls Guide

Real-world issues discovered during proxy architecture debugging. Each pitfall includes symptoms, root cause, and fix.

---

## 1. HK Nodes Dead for OpenAI (Same Exit IP, Different Routing)

**Symptom**: ChatGPT returns `403` or `000` when using HK nodes, but works fine with USA nodes — even though both share the same exit IP.

**Root Cause**: The HK node's entry point routes to OpenAI's backend differently than the USA node's entry point. Same exit IP (`77.247.126.175`), but the HK path to OpenAI's backend returns `000` (TCP timeout).

**Fix**: Exclude HK nodes from AI proxy groups. Use `fallback` with USA/SG nodes first.

**Detection**:
```bash
clash-ai test --proxy http://127.0.0.1:7897 --services chatgpt
```

---

## 2. LU (Luxembourg) Nodes Blocked by Google

**Symptom**: Gemini, Google services intermittently fail with SSL errors or connection resets when using Luxembourg nodes.

**Root Cause**: Google partially blocks the FranTech IP range (`107.189.x.x` / `50.7.x.x`) used by some Luxembourg data centers. The block is intermittent — sometimes works, sometimes doesn't.

**Fix**: Exclude LU nodes from Google-AI groups entirely.

**Detection**:
```bash
clash-ai latency --config config.yaml --json results.json
# Look for LU nodes with high jitter (>1000ms)
```

---

## 3. Gemini iOS Region Detection (Not Just IP)

**Symptom**: Gemini works on desktop browser through proxy, but iOS Gemini app says "not available in your region" even with VPN.

**Root Cause**: Gemini iOS app checks **four** signals:
1. **IP address** (what your proxy changes)
2. **GPS location** (your real physical location — overrides VPN)
3. **SIM carrier** (China Mobile/Unicom = blocked)
4. **Apple ID region** (must match VPN exit country)

**Fix**:
1. iPhone Settings → Privacy → Location Services → Gemini/Google → **Never**
2. iPhone Settings → General → Language & Region → **United States**
3. Use a US Apple ID, or access via `gemini.google.com` in Safari (web version only checks IP)

---

## 4. `url-test` Selecting Jitter Nodes

**Symptom**: Your `url-test` group keeps selecting a node that feels slow, even though its average latency looks good.

**Root Cause**: `url-test` picks by lowest average latency, but ignores **jitter** (max - min). A node averaging 400ms but spiking to 1900ms feels much worse than a stable 600ms node.

Example from real testing:
```
SG-02: [398, 402, 402, 399, 402] → avg 401ms, jitter 4ms → STABLE
SG-01: [1908, 801, 1699, 1502, 1398] → avg 1462ms, jitter 1110ms → UNSTABLE
```

Both are the same physical server (`sg.lyhycloud.org:12002`), but the `-01` entry point has severe jitter.

**Fix**: Use `fallback` instead of `url-test` for high-frequency services. Fallback locks to the first available node (ordered by priority), preventing jumps to jittery nodes.

---

## 5. Cloudflare Bot Management (Not Just Turnstile)

**Symptom**: Services like Perplexity, Mistral, Coinbase, Etherscan return `403` through proxy, but work fine in a real browser.

**Root Cause**: These services use **Cloudflare Bot Management** — a tier above Turnstile. It checks:
- JavaScript execution capability
- Browser fingerprint (canvas, WebGL, fonts)
- IP reputation score
- TLS fingerprint (JA3/JA4)

curl, Python requests, and headless browsers all fail this check. Only real browsers pass.

**Fix**: These services can't be "fixed" through proxy configuration alone. Options:
1. Use residential IP proxy (not datacenter)
2. Accept that curl/API access won't work — use browser only
3. Use the service's official API with an API key (bypasses Bot Management)

**Detection**: If `clash-ai test` shows `403` but the browser works → it's Bot Management.

---

## 6. Shadowrocket Rule Routing Conflicts (Greedy KEYWORD)

**Symptom**: Gemini core domain works but the app shows a blank screen — CSS, JS, fonts, and login all fail.

**Root Cause**: Rule order matters. If you have:
```
DOMAIN-SUFFIX,gemini.google.com,Google-AI     # Core domain ✓
...
DOMAIN-KEYWORD,google,Proxy                    # Auxiliary domains captured by greedy keyword ✗
DOMAIN-SUFFIX,gstatic.com,Proxy                # CSS/JS/fonts go to wrong group ✗
DOMAIN-SUFFIX,google.com,Proxy                 # Login (accounts.google.com) goes wrong ✗
```

The `DOMAIN-KEYWORD,google` rule greedily captures ALL domains containing "google" — including `accounts.google.com`, `apis.google.com`, etc. These auxiliary domains are routed to the wrong proxy group.

**Fix**: Add auxiliary domains to the service-specific group **before** the greedy keyword rule:
```
DOMAIN-SUFFIX,accounts.google.com,Google-AI    # Login
DOMAIN-SUFFIX,www.gstatic.com,Google-AI        # CSS/JS/fonts
DOMAIN-SUFFIX,ssl.gstatic.com,Google-AI        # Secure resources
DOMAIN-SUFFIX,lh3.googleusercontent.com,Google-AI  # Images
```

**Rule**: Always place specific `DOMAIN-SUFFIX` rules before `DOMAIN-KEYWORD` rules. Shadowrocket and Clash match top-to-bottom, first match wins.

---

## 7. Fake Nodes in Subscription (Traffic/Reset/Expiry)

**Symptom**: Your `url-test` group keeps selecting "Remaining Traffic" or "Reset Date" nodes, causing all services to fail.

**Root Cause**: Many airports inject informational nodes into subscriptions (e.g., "剩余流量：995.69 GB"). These aren't real proxy nodes — they're status displays. But `url-test` treats them as real nodes and may select them.

**Fix**: Explicitly exclude informational nodes from proxy groups:
```yaml
# In Clash config
proxy-groups:
  - name: AI-Services
    type: fallback
    proxies:
      - SG-02
      - USA-02
      # Do NOT include: 剩余流量, 距离重置, 套餐到期
```

---

## 8. anytls Cold Start Latency

**Symptom**: First request through a node takes 800-1900ms, subsequent requests are 400ms.

**Root Cause**: The `anytls` protocol has a cold-start TLS handshake cost. If your app doesn't reuse connections (e.g., ChatGPT iOS client creates new connections per request), every request pays this cost.

**Fix**: This is protocol-level — can't fix through config. Options:
1. Switch to a protocol with faster handshake (WireGuard, VLESS+QUIC)
2. Use `lazy: false` in Clash to keep connections warm
3. Accept the latency for first-request, subsequent requests will be faster
