# 订阅端配置优化：连接复用、入口择优与策略组分层

> 本文只讨论**客户端订阅配置**的通用设计，不含任何真实服务端地址、账号、凭证或供应商信息。
> 所有示例值均为占位符，使用前请自行替换。适用于 mihomo / Clash Meta ≥ 1.19、Xray-core ≥ 1.8 的 XHTTP 链路。

## 1. 为什么需要连接复用

XHTTP（前身 SplitHTTP）用一串普通 HTTP 请求承载流量：下行一条长 GET 流式响应，上行多个 POST。相比 WebSocket 的单条长连接，它天然过 HTTP/2 反代、支持并发，但**默认每次请求都要重新完成 TLS + XHTTP 握手**。对于"大量短请求 + 少量长会话"的混合流量（浏览网页、AI 对话），握手开销会主导体感延迟。

解决办法是给 XHTTP 客户端加**有限**连接复用：

```yaml
- name: XH-A
  type: vless
  network: xhttp
  xhttp-opts:
    mode: auto
    path: /<your-path>
    host: <your-host>
    reuse-settings:
      enabled: true
      max-concurrency: 4        # 单连接池并发上限
      c-max-reuse-times: 64     # 单条连接最多复用次数
      h-max-reusable-secs: 300  # 单条连接最长可复用时间（秒）
```

三个约束缺一不可，且**必须是有限值**：

| 参数 | 作用 | 设为无限的风险 |
|---|---|---|
| `c-max-reuse-times` | 防止单连接被无限复用导致状态陈旧 | 连接僵死后不会重建，表现为间歇性 EOF |
| `h-max-reusable-secs` | 定期轮换连接 | 长连接特征固化，且无法感知后端重启 |
| `max-concurrency` | 限制连接池规模 | 瞬时建连过多，触发服务端/中间层限流 |

实测效果（3 MB 下载，同一后端、同样的规则集）：开启有限复用后吞吐约从 11.7 MB/s 提升到 23.5 MB/s，连续 5 次 `generate_204` 探测稳定在 0.09–0.14 s。数值随网络环境变化，建议自行压测后调整，不要照抄。

> 注意：WebSocket 传输没有等价的连接池机制——它靠单条长连接承载全部流量，存在队头阻塞。这是"大流量/长会话优先 XHTTP"的根本原因，不是配置偏好问题。

## 2. 端侧入口择优

同一个后端可以暴露多个入口（例如不同边缘 IP、不同 DNS 解析方式、不同传输协议）。把它们全部下发给客户端，由客户端自动择优，比服务端做调度更稳：

```yaml
- name: Entry-Auto
  type: url-test
  url: http://www.gstatic.com/generate_204
  interval: 120
  lazy: false
  tolerance: 50
  proxies: [XH-A, WS-A, XH-B, WS-B]
```

要点：

- **探测目标选 `generate_204`**：返回 204、无内容、开销极小，且不会被登录页/ captive portal 的 200 响应误判为可用。
- **`lazy: false`**：持续探测，切换更及时；若客户端流量极小、想省电，可改 `true`（仅被选中时才测）。
- **`tolerance`**：避免在两个入口 RTT 接近时反复抖动切换。
- **固定 IP 入口 vs DNS 入口**：把实测最优的边缘地址直接写进节点，通常明显快于让系统 DNS 就近解析；但固定地址会失效，所以**必须**同时保留一组走 DNS 的兜底节点。两者共存，不要二选一。

## 3. 策略组分层的分工

不要让所有流量共用一个自动选择组。按流量特征拆开：

| 组类型 | 适用流量 | 理由 |
|---|---|---|
| `url-test` | 通用网页、下载 | 追求最低延迟，可随时切换节点 |
| `fallback` | AI 对话、长会话、流式响应 | **避免在会话中途切换节点**导致连接中断；按成员顺序兜底 |
| `load-balance` | 大文件下载 | 多流并发，绕开单连接限速 |
| `select` | 手动兜底 | 自动组全部异常时给人一个手动出口 |

一个常见错误是把 AI 组也设成 `url-test`：健康检查每 120 s 触发一次，一旦最优节点变化，正在进行的流式回答会被切断。AI 组用 `fallback` + `lazy: true`，只在当前节点确实失败时才降级。

## 4. iOS / 老客户端兼容

Stash、Shadowrocket、Loon 等客户端对 `network: xhttp` 的支持不一致，部分版本完全无法解析该节点。因此订阅里**必须保留一组 WebSocket 入口**，并单独提供一个只含 WS 节点的订阅端点（如 `/ios`）。

不要为了"配置看起来统一"把 WS 节点删掉——那会让 iOS 端直接不可用。WS 入口在支持 XHTTP 的客户端上也可作为降级项，不算冗余。

## 5. 订阅应是「纯代理配置」

订阅文件**只**下发 `proxies` / `proxy-groups` / `rules`，不要覆盖客户端本地设置：

```yaml
# 以下字段一律不要出现在订阅里
# port / socks-port / mixed-port / allow-lan
# external-controller / secret
# dns / tun / hosts
```

原因：用户本地往往已有固定的混合端口（例如 Clash Verge 的 7897）、独立的 DNS 配置和控制面板。订阅一旦覆盖，轻则端口冲突，重则整个客户端启动失败——历史上出现过"电脑版全部 timeout"，根因就是订阅里带了 `dns` 和 `external-controller` 覆盖。

## 6. 规则内嵌，不依赖外部规则库

早期方案常引用 `geosite.dat` / `geoip.dat` 的远程 URL，移动端网络下下载失败会导致规则加载不全甚至客户端启动崩溃。**把实际需要的规则直接内嵌进订阅**，零外部依赖：

```yaml
rules:
  # AI 服务走专用组
  - DOMAIN-SUFFIX,openai.com,AI-Proxy
  - DOMAIN-SUFFIX,chatgpt.com,AI-Proxy
  - DOMAIN-SUFFIX,anthropic.com,AI-Proxy
  - DOMAIN-SUFFIX,claude.ai,AI-Proxy
  - DOMAIN-SUFFIX,generativelanguage.googleapis.com,AI-Proxy
  # 国内直连
  - DOMAIN-SUFFIX,baidu.com,DIRECT
  - DOMAIN-SUFFIX,qq.com,DIRECT
  - GEOSITE,cn,DIRECT
  # 兜底
  - MATCH,Proxy
```

## 7. 可选加固（针对网络层指纹）

这两项属于**另一个威胁模型**，按需要决定是否启用：

- `client-fingerprint: chrome`（proxy **顶层**字段，不是校验证书用的 `fingerprint`）：让 uTLS 握手指纹贴近浏览器。
- `ech-opts: { enable: true, config: "<DoH 提供的 ECH 配置>" }`（同为顶层）：加密 SNI。

字段名以 mihomo 官方文档为准，写错位置会静默失效。

## 8. 上线前验证清单

1. `mihomo -t -f config.yaml` 语法通过（**必须**，占位符替换后尤其要跑）。
2. `generate_204` 连续 5 次，观察延迟稳定性而非单次最低值。
3. 逐组验证：通用网页、AI 对话、流式回答、大文件下载、国内站点直连。
4. 检查订阅里是否残留本地端口 / DNS / 控制器字段。
5. 检查 `proxies` 中是否存在悬空引用（组里点名了不存在的节点）。
6. 在至少一种 iOS 客户端上导入 `/ios` 订阅，确认 WS 节点可解析。

## 小结

真正影响体感的是三件事：**有限连接复用**摊薄握手开销、**端侧入口择优**避开次优路径、**策略组按流量特征分层**避免长会话被打断。这三件事都与具体服务端无关，可以安全地作为通用策略沉淀到配置生成器里。
