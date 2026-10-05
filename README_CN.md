# OneMi

**一套配置，三端通用。专为 AI 服务优化的 Clash 代理架构。**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version 1.1](https://img.shields.io/badge/version-1.1-blue.svg)](#更新日志)

> 📖 [English](README.md) | **中文**

```
OneMi/
├── OneMi-S24-ClashMeta.yaml         # 三星 S24 / 安卓 + ClashMeta
├── OneMi-Windows-ClashVerge.yaml     # Windows + Clash Verge Rev
├── OneMi-iPhone-YAML.yaml            # iPhone + mihomo 内核（ProxyMD 等）
├── OneMi-iPhone-Shadowrocket.conf    # iPhone + Shadowrocket（原生 .conf）
├── clash_ai_proxy/                   # CLI 工具源码（节点测速 + 自动生成）
├── templates/                        # 模板文件
├── docs/pitfalls.md                  # 踩坑记录
└── gen_onemi.py                      # 从主配置生成四端文件
```

---

## 这是什么？

OneMi 是一套**单源多端、AI 优先**的 Clash 代理配置架构。写一次规则，跑一个脚本，就能生成 Windows、安卓、iPhone 三端配置——共享同一套 12 策略组、150+ 条规则的架构，专门为 AI 服务调优。

### 为什么不直接用别人的 Clash 配置？

大多数 Clash 配置把 AI 服务当普通网站对待——扔进一个通用"代理"组就完事。OneMi 是基于上百小时真实调试经验构建的：

- **ChatGPT 在香港节点死链**，但美国节点正常——同一个出口 IP，路由路径不同
- **Gemini 在卢森堡 IP 被封**——Google 拒绝某些 FranTech IP 段
- **Claude 用 curl 返回 403**，但浏览器正常——Cloudflare Bot Management
- **anytls 冷启动 1900ms**，首条请求慢，后续 400ms——需要 `lazy: false` 预热
- **Shadowrocket 贪婪匹配 `KEYWORD,google`** 会捕获 Gemini 辅助域名 → 白屏

详见 [`docs/pitfalls.md`](docs/pitfalls.md)。

---

## 12 策略组架构

| # | 策略组 | 类型 | 覆盖服务 | 为什么单独分组 |
|---|--------|------|----------|----------------|
| 1 | **Google-AI** | fallback | Gemini、NotebookLM、AI Studio | Google 封禁特定 IP 段 |
| 2 | **AI-Proxy** | url-test | ChatGPT、Claude、Grok | OpenAI 死节点检测（其他服务正常但 OpenAI 不通） |
| 3 | **Note-Tools** | url-test | Notion、Obsidian、Craft | 低风险，选最快 |
| 4 | **Dev-AI** | url-test | Cursor、Copilot、Replit | 低风险 |
| 5 | **CF-Strict** | select | Perplexity、Mistral、Poe | Cloudflare Bot Management——需手动选节点 |
| 6 | **Social** | fallback | Telegram、Discord、WhatsApp | 高频使用，需要稳定性 |
| 7 | **Dev-Svc** | fallback | Docker、PyPI、npm、Vercel | 高频使用 |
| 8 | **Web3** | fallback | Binance、Coinbase、DeFi | 交易所地区限制不同 |
| 9 | **Finance** | fallback | Bloomberg、Reuters、NYT | 财经新闻地区限制 |
| 10 | **Game-Media** | fallback | Netflix、YouTube、Spotify | 保持会话连续性 |
| 11 | **Shopping** | fallback | Amazon、eBay、Zara | 电商地区限制 |
| 12 | **Proxy** | url-test | 其他所有流量 | 兜底 |

### 为什么 AI 用 fallback 而不是 url-test？

| | `url-test` | `fallback` |
|---|---|---|
| 选择依据 | 到测试 URL 的最低延迟 | 第一个可用节点（按优先级排序） |
| 问题 | 对 gstatic 快 ≠ 对 OpenAI 可用 | 健康检查用**真实服务地址** |
| 行为 | 不断跳到"最快"节点 | 保持当前节点直到故障 |

---

## 快速开始

### 方式 A：直接使用 OneMi 配置文件

```bash
# 克隆仓库
git clone https://github.com/MiLab-Bit/clash-ai-proxy.git
cd clash-ai-proxy
```

四端配置文件已就绪，根据你的设备选择：

| 设备 | 文件 | 导入方式 |
|------|------|----------|
| **Windows** | `OneMi-Windows-ClashVerge.yaml` | Clash Verge Rev → 配置 → 导入 |
| **安卓 (S24)** | `OneMi-S24-ClashMeta.yaml` | ClashMeta → 配置 → 从文件导入 |
| **iPhone (mihomo)** | `OneMi-iPhone-YAML.yaml` | ProxyMD → 配置 → 导入 |
| **iPhone (Shadowrocket)** | `OneMi-iPhone-Shadowrocket.conf` | Shadowrocket → 配置 → 还原 |

### ⚠️ 使用前必做：替换占位符

配置文件中的敏感字段已占位化，**导入前替换为你的真实值**：

| 占位符 | 替换成什么 | 在文件中的位置 |
|--------|-----------|----------------|
| `YOUR_SUBSCRIBE_TOKEN` | 你的机场订阅 token | `proxy-providers.fightlyd.url` |
| `YOUR_NODE_PASSWORD` | 你的节点密码 | `proxies` 中每个节点的 `password` |
| `YOUR_S24_DASHBOARD_SECRET` | 自定义 dashboard 密码 | `secret` |
| `YOUR_WIN_DASHBOARD_SECRET` | 自定义 dashboard 密码 | `secret` |

> 如果你用机场订阅（proxy-providers），只需替换 `YOUR_SUBSCRIBE_TOKEN`，不需要手填节点。
> 如果你用手贴节点（proxies），需要替换 `YOUR_NODE_PASSWORD` 和 `secret`。

### 方式 B：用 CLI 工具自动生成

```bash
pip install clash-ai-proxy

# 测试哪些节点能访问 AI 服务
clash-ai test --proxy http://127.0.0.1:7897

# 测试节点延迟稳定性
clash-ai latency --config config.yaml

# 自动生成优化配置（排除死节点）
clash-ai generate --config config.yaml --output optimized.yaml
```

---

## 配置里有什么？（2026 年最佳实践）

### 引擎级优化

| 设置 | 值 | 原因 |
|------|-----|------|
| `tcp-concurrent` | `true` | 并行 TCP 竞速，自动选最快路径 |
| `geodata-mode` | `true` | `.dat` 格式，内存占用减少 40% |
| `keep-alive-interval` | `30` | 降低保活频率，省电 |
| `global-client-fingerprint` | `chrome` | 统一 TLS 指纹 |
| `find-process-mode` | `off`（手机）/ `off`（电脑） | 手机：省 procfs 开销；电脑：不误伤 svchost |
| `unified-delay` | `true` | 统一延迟计算，消除首次偏高 |

### DNS 架构

| 层 | 作用 |
|----|------|
| `enhanced-mode: fake-ip` | 代理域名不泄漏 DNS |
| `nameserver-policy` 按 GEOSITE 分流 | 国内域名→国内 DoH，AI 域名→Google DoH，Apple/MS→国内 DoH |
| `direct-nameserver` + `follow-policy` | 直连流量 DNS 不经过代理 |
| `geosite:category-ads-all → rcode://success` | 广告域名返回空（无"加载中"转圈） |
| `store-fake-ip: true` | 持久化 fake-ip，重载配置后 AI 长连接不用重新握手 |
| `cache-algorithm: arc` | 比 LRU 更高的 DNS 缓存命中率 |

### TUN 配置

| 平台 | 协议栈 | MTU | 说明 |
|------|--------|-----|------|
| 安卓 | `mixed`（TCP=系统 + UDP=gvisor） | `1500` | ROM 兼容性最好 |
| Windows | `gvisor` | 默认 | 不需要管理员权限 |
| iOS | `system` | 默认 | iOS 限制 |

DNS 劫持：`any:53` + `tcp://any:53`（部分 App 用 TCP DNS）。

### Sniffer — 稳定模式

```yaml
sniffer:
  parse-pure-ip: false          # 不嗅探纯 IP（会破坏银行 App）
  override-destination: false   # 不覆盖目标（会破坏证书固定 App）
  skip-domain:                  # 完全跳过这些域名
    - "+.icbc.com.cn"           # 工商银行
    - "+.apple.com"             # Apple 证书固定
    - "+.icloud.com"            # iCloud 证书固定
```

### 规则排序

```
私有网络 → AI GEOSITE → AI 静态资源 → Apple/MS 直连 →
国内域名 → 国内 IP → 广告拦截 → MATCH 兜底
```

- **不用 `DOMAIN-KEYWORD`** 匹配 AI 服务——太宽泛（`openai.example-blog.com` 也会命中）
- **AI 静态域名单独路由**（oaistatic、anthropicusercontent 等）——修复"聊天能用但图片/CSS 加载不出来"
- **Apple/Microsoft → DIRECT**——中国区 App Store / iCloud / Office
- **`GEOIP,CN,no-resolve`**——fake-ip 下不反解 CN IP，速度更稳

### MRS 原生规则集

使用 mihomo 的 `.mrs` 格式（二进制，解析更快，体积更小），全部走 MetaCubeX **meta 分支**（直连 200，无 302 跳转）：

| 规则集 | 用途 |
|--------|------|
| `geosite/category-ai-chat-!cn.mrs` | 非中国 AI 服务总集 |
| `geosite/cn.mrs` | 国内域名 |
| `geosite/category-ads-all.mrs` | 广告拦截 |
| `geoip/cn.mrs` | 国内 IP 段 |

### 安全

- 所有节点 `skip-cert-verify: false`（anytls 本身不验证 TLS）
- `secret` 使用随机强密码（非字典密码）
- `allow-lan: false`（默认不开放局域网）

### 省电（手机端）

- 所有策略组 `lazy: true` + `interval: 300`（之前 120-180s + lazy:false 太频繁）
- `find-process-mode: off`（无 procfs 开销）

---

## 端专属差异

| 差异点 | S24 (安卓) | Windows | iPhone (mihomo) | iPhone (Shadowrocket) |
|--------|------------|---------|-----------------|----------------------|
| 端口 | 1053 | 1053 | 7890 | — |
| strict-route | true | — | false | 无效 |
| dns.listen | 无 | 无 | 无 | — |
| external-controller | 127.0.0.1:9097 | pipe | 无 | — |
| Apple APNs 推送 | 不需要 | 不需要 | 需要（专属规则） | 需要 |
| Samsung GMS 推送 | 需要（专属规则） | 不需要 | 不需要 | 不需要 |
| find-process-mode | off | off | off | — |
| 规则数 | 157 | 156 | 169 | 140 |
| 规则语法 | GEOSITE / RULE-SET | GEOSITE / RULE-SET | GEOSITE / RULE-SET | DOMAIN-SUFFIX / FINAL |

---

## 对比

| 功能 | [Loyalsoldier](https://github.com/Loyalsoldier/clash-rules) (18k★) | [blackmatrix7](https://github.com/blackmatrix7/ios_rule_script) (20k★) | **OneMi** |
|------|-----|-----|-----|
| 提供什么 | 域名规则列表 | 按服务拆分的规则文件 | **完整架构 + 配置 + CLI** |
| AI 专属路由 | ❌ | 仅规则文件 | **✅ 按服务健康检查** |
| 多设备同步 | ❌ | ❌ | **✅ 一套配置 → 三端生成** |
| 死节点检测 | ❌ | ❌ | **✅ CLI 逐节点测试** |
| 延迟稳定性测试 | ❌ | ❌ | **✅ 抖动检测** |
| 自动排除坏节点 | ❌ | ❌ | **✅ 生成器自动跳过** |
| 2026 mihomo 特性 | ❌ | ❌ | **✅ MRS / GEOSITE DNS / store-fake-ip** |

> **这些项目互补。** 规则项目管*域名*，OneMi 管*节点 + 架构*。配合使用效果最好。

---

## CLI 命令参考

```bash
# 测试 AI 服务可达性
clash-ai test --proxy http://127.0.0.1:7897

# 测试节点延迟（5 次采样，抖动检测）
clash-ai latency --config config.yaml --samples 5

# 生成配置（Clash YAML 或 Shadowrocket conf）
clash-ai generate --config config.yaml --output optimized.yaml
clash-ai generate --config config.yaml --format shadowrocket --output optimized.conf

# 全流程：测试 + 分类 + 生成
clash-ai full --config config.yaml --proxy http://127.0.0.1:7897
```

---

## 支持的服务

| 分类 | 服务 |
|------|------|
| **AI** | ChatGPT、Claude、Gemini、Grok、Perplexity、Cursor、Copilot、Cohere、Mistral、Poe、HuggingFace、arxiv |
| **流媒体** | Netflix、YouTube、Disney+、HBO、Prime Video、Spotify、Crunchyroll |
| **社交** | Telegram、Discord、Twitter/X、WhatsApp、Instagram、Reddit |
| **开发** | GitHub、Docker、PyPI、npm、Vercel、Supabase |
| **Web3** | Binance、Coinbase、OKX、MetaMask、Etherscan |
| **直连** | Apple、iCloud、Microsoft、Samsung、Steam CDN、Tailscale |

---

## 适合谁用？

- ✅ 你用 **Clash / mihomo / ClashMeta / Shadowrocket** 且有多个节点
- ✅ 你访问 **AI 服务**（ChatGPT、Claude、Gemini）需要**稳定可用**
- ✅ 你有**多台设备**（电脑 + 手机）想用同一套配置
- ✅ 你想要 **2026 年最佳实践**（MRS 规则集、GEOSITE DNS、fake-ip 持久化）

不适合：只用单个节点的人，或不访问地区限制服务的人。

---

## 从源码生成

```bash
# 编辑 OneMi-S24-ClashMeta.yaml（主配置）
# 然后生成所有平台：
python gen_onemi.py
# → OneMi-Windows-ClashVerge.yaml
# → OneMi-iPhone-YAML.yaml
# → OneMi-iPhone-Shadowrocket.conf
```

---

## 更新日志

### v1.1 — 安全 + MRS 优化（2026-10-05）

| 改动 | 说明 |
|------|------|
| **凭证占位化** | 所有配置文件中的订阅 token / 节点密码 / dashboard 密码替换为 `YOUR_*` 占位符 |
| **MRS URL 统一 meta 分支** | 从 `releases/latest/download` 改为 `raw.../meta/geo/`（直连 200，无 302） |
| **0.0.0.0/32 清除** | fallback-filter.ipcidr 删除纯噪音 IP |
| **广告去重** | S24 删 googleadservices/googlesyndication 单条 REJECT；iPhone 合并重复规则集引用 |

### v1.0 — OneMi 品牌统一（2026-10-05）

| 改动 | 说明 |
|------|------|
| **OneMi 品牌** | 所有配置统一为 OneMi，文件格式：`OneMi-{设备}-{App}.{ext}` |
| **proxy-providers 架构** | 删 13 个手贴节点，改用 proxy-providers 自动拉取机场订阅 |
| **gen_onemi.py** | 从一份主 YAML 生成 Windows/安卓/iPhone 配置 |
| **MRS 原生规则集** | `.mrs` 格式（geosite-ai/cn/ads + geoip-cn）——解析更快，体积更小 |
| **DNS 按 GEOSITE 分流** | `nameserver-policy` 用 `geosite:cn` / `geosite:google` 等，替代手写域名列表 |
| **广告静默拦截** | `geosite:category-ads-all → rcode://success`（DNS 层，无"加载中"转圈） |
| **AI 静态资源** | oaistatic、anthropicusercontent、files.chatgpt、cdn.anthropic、static.claude——修复"聊天能用但图片加载不出来" |
| **删除 DOMAIN-KEYWORD** | 所有关键字规则已删——太宽泛，GEOSITE + DOMAIN-SUFFIX 更精确 |
| **store-fake-ip** | 持久化 fake-ip——重载配置后 AI 长连接不用重新握手 |
| **cache-algorithm: arc** | 比 LRU 更高的 DNS 缓存命中率 |
| **省电优化** | 所有策略组 `lazy: true` + `interval: 300`——手机后台测试更少 |

---

## 许可证

[MIT](LICENSE)
