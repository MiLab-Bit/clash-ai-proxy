"""
Config generator — generates optimized Clash/mihomo and Shadowrocket configs
based on node test results.

v1.3.0 (v5 收尾版) changes:
- skip-cert-verify default false (was true — MITM attack surface too wide for banking/enterprise)
- sniffer stable mode (parse-pure-ip: false, override-destination: false, + skip-domain for banks/Apple)
- TUN enabled by default (makes sniffer/rules effective for CLI, games, and non-browser apps)
- GEOSITE,category-ads-all added (full ad-block, replaces partial manual rules)
- Apple/Microsoft/Cloudflare/Tailscale/Steam 国区 rules completed (19 rules)
- GEOSITE rule group names fixed (Dev-Tools → Dev-Svc)

v1.2.0 (v5 config) changes:
- tcp-concurrent: true (parallel TCP connections, auto-select fastest path)
- sniffer enabled (restore real domain from TLS SNI, makes DOMAIN rules work under fake-ip)
- geodata-mode: true (dat format instead of mmdb, -40% memory, faster GeoIP lookups)
- GeoSite rules (GEOSITE,google covers 200+ domains vs our manual 20)
- DNS nameserver-policy (AI domains use Google DoH directly, -200ms latency)
- max-failed-times: 3 (auto-switch node after 3 consecutive failures)
- keep-alive-interval: 30 (reduced keepalive frequency, saves battery on mobile)
- global-client-fingerprint: chrome (unified TLS fingerprint, cleaner configs)

v1.1.0 changes:
- lazy: false on all proxy groups (keep connections warm, avoid anytls cold start)
- fake-ip-filter includes AI domains (prevents DNS leak for AI traffic)
- rule-providers support (blackmatrix7 remote rulesets, daily auto-update)
- Node priority ordering (-02 nodes first, proven more stable in practice)
- IPv6 disabled by default (many airports lack IPv6, causes leaks)
- DNS fallback to DoH (1.1.1.1) for reliability
"""
import yaml
from typing import Dict, List, Optional


# 11-layer architecture template (v5)
# Each group can specify:
#   - priority_pattern: regex to sort nodes (e.g., "-02$" puts -02 nodes first)
#   - exclude_pattern: regex to exclude nodes (e.g., "UK|Warp" drops UK and Warp-CF)
#   - lazy: false — keep connections warm (default for all groups now)
#   - max_failed_times: 3 — auto-switch node after 3 consecutive failures
ARCHITECTURE = {
    "groups": [
        {
            "name": "Google-AI",
            "type": "fallback",
            "services": ["gemini"],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "lazy": False,
            "priority_pattern": r"-02$",
            "exclude_pattern": r"LU|UK",
            "comment": "Gemini — exclude LU (Google IP block) + UK (jitter), -02 priority",
        },
        {
            "name": "AI-Services",
            "type": "fallback",
            "services": ["chatgpt", "claude", "grok", "perplexity"],
            "health_url": "https://chatgpt.com/cdn-cgi/trace",
            "interval": 300,
            "lazy": False,
            "priority_pattern": r"-02$",
            "exclude_pattern": r"HK|UK",
            "comment": "ChatGPT/Claude/Grok — exclude HK (dead for OpenAI) + UK (jitter), -02 priority",
        },
        {
            "name": "CF-Strict",
            "type": "select",
            "services": ["perplexity", "mistral", "poe"],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "exclude_pattern": r"HK|UK|JP-01",
            "comment": "Cloudflare Bot Management services — manual selection, exclude known bad nodes",
        },
        {
            "name": "Social",
            "type": "fallback",
            "services": ["telegram", "discord", "twitter", "whatsapp"],
            "health_url": "https://discord.com/api/v1/ping",
            "interval": 120,
            "lazy": False,
            "priority_pattern": r"-02$",
        },
        {
            "name": "Streaming",
            "type": "fallback",
            "services": ["netflix", "youtube", "disney", "hbo", "primevideo", "crunchyroll", "spotify"],
            "health_url": "https://www.youtube.com",
            "interval": 180,
            "lazy": False,
        },
        {
            "name": "Dev-Svc",
            "type": "fallback",
            "services": ["github", "docker", "pypi", "npm", "vercel"],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "lazy": False,
            "priority_pattern": r"-02$",
            "comment": "Dev services — high frequency, keep warm",
        },
        {
            "name": "Dev-AI",
            "type": "url-test",
            "services": ["cursor", "github_copilot", "replit"],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 50,
            "comment": "Dev AI — low stakes, url-test acceptable",
        },
        {
            "name": "Web3",
            "type": "fallback",
            "services": ["binance", "coinbase", "opensea"],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 180,
            "lazy": False,
            "priority_pattern": r"-02$",
        },
        {
            "name": "Finance",
            "type": "fallback",
            "services": [],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 180,
            "lazy": False,
            "priority_pattern": r"-02$",
        },
        {
            "name": "Shopping",
            "type": "fallback",
            "services": [],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 180,
            "lazy": False,
        },
        {
            "name": "Proxy",
            "type": "url-test",
            "services": [],
            "health_url": "https://www.gstatic.com/generate_204",
            "interval": 180,
            "tolerance": 50,
            "exclude_pattern": r"UK|Warp",
            "comment": "Fallback for all other proxied traffic",
        },
    ]
}


# Domains to add to fake-ip-filter (these should use real DNS, not fake-ip)
# AI services need real DNS to avoid detection; streaming needs real DNS for CDN
FAKE_IP_FILTER_DOMAINS = [
    "+.openai.com",
    "+.chatgpt.com",
    "+.anthropic.com",
    "+.claude.ai",
    "+.gemini.google.com",
    "+.generativelanguage.googleapis.com",
    "+.netflix.com",
    "+.nflxvideo.net",
    "+.disneyplus.com",
    "rule-set:fakeip-filter/system",
]

# v5: DNS nameserver-policy — AI domains use Google DoH directly (-200ms latency)
NAMESERVER_POLICY = {
    "+.openai.com": "https://dns.google/dns-query",
    "+.chatgpt.com": "https://dns.google/dns-query",
    "+.oaistatic.com": "https://dns.google/dns-query",
    "+.anthropic.com": "https://dns.google/dns-query",
    "+.claude.ai": "https://dns.google/dns-query",
    "+.gemini.google.com": "https://dns.google/dns-query",
    "+.generativelanguage.googleapis.com": "https://dns.google/dns-query",
    "+.perplexity.ai": "https://dns.google/dns-query",
    "+.x.ai": "https://dns.google/dns-query",
}

# v5: GeoSite rule mappings (complement manual domain lists)
GEOSITE_RULES = [
    "GEOSITE,openai,AI-Services",
    "GEOSITE,anthropic,AI-Services",
    "GEOSITE,gemini,Google-AI",
    "GEOSITE,google,Proxy",
    "GEOSITE,youtube,Streaming",
    "GEOSITE,telegram,Social",
    "GEOSITE,discord,Social",
    "GEOSITE,netflix,Streaming",
    "GEOSITE,spotify,Streaming",
    "GEOSITE,github,Dev-Svc",       # v1.3: was "Dev-Tools" (typo, group doesn't exist)
    "GEOSITE,docker,Dev-Svc",       # v1.3: was "Dev-Tools"
    "GEOSITE,cn,DIRECT",
    "GEOSITE,category-ads-all,REJECT",  # v1.3 收尾: full ad-block
]

# v1.3 收尾: sniffer skip-domain — domains that should NOT be sniffed
# (banking apps, enterprise VPN, cert-pinned services can break if sniffer overrides)
SNIFFER_SKIP_DOMAINS = [
    "+.icbc.com.cn",       # ICBC
    "+.cmbchina.com",      # CMB
    "+.bankcomm.com",      # Bank of Communications
    "Mijia Cloud",         # Mijia smart home
    "+.apple.com",         # Apple (cert-pinned, push notification)
    "+.icloud.com",        # iCloud (cert-pinned)
    "+.bank.example",      # Placeholder for user's bank
]

# v1.3 收尾: TUN configuration (makes sniffer/rules work for ALL apps, not just browsers)
TUN_CONFIG = {
    "enable": True,
    "stack": "gvisor",        # gvisor = best compatibility (use "system" for Android)
    "dns-hijack": ["any:53"],
    "auto-route": True,
    "auto-redirect": True,
    "auto-detect-interface": True,
}


# Rule providers (remote rulesets from blackmatrix7 — daily auto-update)
RULE_PROVIDERS = {
    "openai-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.yaml",
        "path": "./ruleset/blackmatrix7/openai.yaml",
        "interval": 86400,
    },
    "gemini-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Gemini/Gemini.yaml",
        "path": "./ruleset/blackmatrix7/gemini.yaml",
        "interval": 86400,
    },
    "claude-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Claude/Claude.yaml",
        "path": "./ruleset/blackmatrix7/claude.yaml",
        "interval": 86400,
    },
    "copilot-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/GithubCopilot/GithubCopilot.yaml",
        "path": "./ruleset/blackmatrix7/copilot.yaml",
        "interval": 86400,
    },
    "telegram-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Telegram/Telegram.yaml",
        "path": "./ruleset/blackmatrix7/telegram.yaml",
        "interval": 86400,
    },
    "netflix-direct": {
        "type": "http",
        "behavior": "classical",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Netflix/Netflix.yaml",
        "path": "./ruleset/blackmatrix7/netflix.yaml",
        "interval": 86400,
    },
}


import re


def _sort_nodes_by_priority(node_names: List[str], group_def: Dict) -> List[str]:
    """
    Sort nodes by priority pattern and apply exclusions.

    - exclude_pattern: drop nodes matching this regex
    - priority_pattern: nodes matching this regex go first
    """
    result = list(node_names)

    # Apply exclusions
    exclude_pat = group_def.get("exclude_pattern")
    if exclude_pat:
        result = [n for n in result if not re.search(exclude_pat, n, re.IGNORECASE)]

    # Apply priority ordering
    priority_pat = group_def.get("priority_pattern")
    if priority_pat:
        priority = [n for n in result if re.search(priority_pat, n, re.IGNORECASE)]
        others = [n for n in result if not re.search(priority_pat, n, re.IGNORECASE)]
        result = priority + others

    return result


def generate_clash_config(
    nodes: List[Dict],
    test_results: Optional[Dict[str, Dict]] = None,
    excluded_nodes: Optional[List[str]] = None,
    use_rule_providers: bool = True,
) -> str:
    """
    Generate a Clash/mihomo YAML config based on available nodes and test results.

    Args:
        nodes: List of node dicts with 'name', 'type', 'server', 'port', etc.
        test_results: Optional dict of {node_name: {service: result_dict}}
        excluded_nodes: Optional list of node names to exclude from all groups
        use_rule_providers: If True, include blackmatrix7 rule-providers for better rule coverage

    Returns:
        Complete YAML config string
    """
    excluded = set(excluded_nodes or [])

    # Auto-exclude dead/unstable nodes if test results provided
    if test_results:
        for node_name, results in test_results.items():
            classification = results.get("classification")
            if classification in ("dead", "region-blocked"):
                excluded.add(node_name)

    # Filter available nodes
    available = [n for n in nodes if n["name"] not in excluded]

    # v1.3 收尾: Force skip-cert-verify: false on all nodes
    # Was true by default (copied from airport subscription) — MITM attack surface too wide
    # for banking/enterprise services. mihomo doesn't verify TLS for anytls anyway.
    sanitized = []
    for n in available:
        node = dict(n)  # shallow copy to avoid mutating caller's dict
        node["skip-cert-verify"] = False
        sanitized.append(node)

    node_names = [n["name"] for n in sanitized]

    config = {
        "mixed-port": 7890,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,  # Disabled — many airports lack IPv6, causes leaks
        "external-controller": "127.0.0.1:9090",
        # v5 global optimizations
        "tcp-concurrent": True,           # Parallel TCP connections, auto-select fastest
        "geodata-mode": True,             # dat format, -40% memory
        "keep-alive-interval": 30,        # Reduced keepalive, saves battery
        "global-client-fingerprint": "chrome",  # Unified TLS fingerprint
        "sniffer": {                      # v1.3 收尾: stable mode
            "enable": True,
            "force-dns-mapping": True,
            "parse-pure-ip": False,          # 收尾: was True — breaks banking/enterprise apps
            "override-destination": False,   # 收尾: was True — breaks cert-pinned apps
            "sniff": {
                "TLS": {"ports": [443, 8443]},
                "HTTP": {"ports": [80, 8080, 8880]},
                "QUIC": {"ports": [443, 8443]},
            },
            "skip-domain": SNIFFER_SKIP_DOMAINS,
        },
        "tun": TUN_CONFIG,            # v1.3 收尾: TUN on — CLI/games/apps also go through rules
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "fake-ip-filter": FAKE_IP_FILTER_DOMAINS,
            "nameserver": ["https://doh.pub/dns-query", "https://dns.alidns.com/dns-query"],
            "fallback": ["https://1.1.1.1/dns-query", "https://dns.google/dns-query"],
            "nameserver-policy": NAMESERVER_POLICY,  # v5: AI domains → Google DoH
            "fallback-filter": {
                "geoip": True,
                "geoip-code": "CN",
            },
        },
        "proxies": sanitized,
        "proxy-groups": [],
        "rules": [],
    }

    # Add rule-providers if enabled
    if use_rule_providers:
        config["rule-providers"] = RULE_PROVIDERS

    # Generate proxy groups
    for group_def in ARCHITECTURE["groups"]:
        # Sort nodes by priority and apply exclusions for this group
        group_nodes = _sort_nodes_by_priority(node_names, group_def)

        # Apply per-service exclusions based on test results
        if test_results and group_def["services"]:
            service_excluded = set()
            for svc in group_def["services"]:
                for node_name, results in test_results.items():
                    svc_result = results.get("services", {}).get(svc, {})
                    if svc_result and not svc_result.get("reachable"):
                        service_excluded.add(node_name)
            group_nodes = [n for n in group_nodes if n not in service_excluded]

        if not group_nodes:
            group_nodes = node_names  # fallback to all if all excluded

        group = {
            "name": group_def["name"],
            "type": group_def["type"],
            "proxies": group_nodes,
            "url": group_def["health_url"],
            "interval": group_def["interval"],
        }

        # Add lazy: false for fallback/url-test groups (keep connections warm)
        if "lazy" in group_def:
            group["lazy"] = group_def["lazy"]
        elif group_def["type"] in ("fallback", "url-test"):
            group["lazy"] = False

        # v5: Add max-failed-times for fallback groups (auto-switch after 3 failures)
        if group_def["type"] == "fallback":
            group["max-failed-times"] = group_def.get("max_failed_times", 3)

        if group_def["type"] == "url-test":
            group["tolerance"] = group_def.get("tolerance", 50)

        config["proxy-groups"].append(group)

    # Generate rules
    rules = _generate_rules(use_rule_providers=use_rule_providers)
    config["rules"] = rules

    return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _generate_rules(use_rule_providers: bool = False) -> List[str]:
    """Generate the rule list mapping domains to proxy groups.

    Args:
        use_rule_providers: If True, use RULE-SET rules (blackmatrix7 remote rulesets)
                           for better coverage instead of manual domain lists.
    """
    rules = []

    if use_rule_providers:
        # Use remote rulesets (blackmatrix7) — better coverage, auto-updated daily
        rules.append("RULE-SET,gemini-direct,Google-AI")
        rules.append("RULE-SET,claude-direct,AI-Services")
        rules.append("RULE-SET,openai-direct,AI-Services")
        rules.append("RULE-SET,copilot-direct,Dev-AI")
        rules.append("RULE-SET,telegram-direct,Social")
        rules.append("RULE-SET,netflix-direct,Streaming")

        # v5: GeoSite rules — complement manual domain lists with 200+ domains per category
        for geosite_rule in GEOSITE_RULES:
            rules.append(geosite_rule)

    # Google AI — auxiliary domains MUST come before greedy KEYWORD rules
    ai_domains = [
        "gemini.google.com", "generativelanguage.googleapis.com", "aistudio.google.com",
        "bard.google.com", "ai.google.dev", "deepmind.google", "notebooklm.google.com",
        "makersuite.google.com", "accounts.google.com", "www.gstatic.com", "ssl.gstatic.com",
        "lh3.googleusercontent.com",
    ]
    for d in ai_domains:
        rules.append(f"DOMAIN-SUFFIX,{d},Google-AI")
    rules.append("DOMAIN-KEYWORD,gemini,Google-AI")
    rules.append("DOMAIN-KEYWORD,notebooklm,Google-AI")

    # AI Services
    ai_svc = [
        "claude.ai", "anthropic.com", "x.ai", "grok.com", "cohere.com",
        "character.ai", "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com",
        "perplexity.ai", "mistral.ai", "poe.com",
    ]
    for d in ai_svc:
        rules.append(f"DOMAIN-SUFFIX,{d},AI-Services")
    rules.append("DOMAIN-KEYWORD,claude,AI-Services")
    rules.append("DOMAIN-KEYWORD,anthropic,AI-Services")
    rules.append("DOMAIN-KEYWORD,openai,AI-Services")
    rules.append("DOMAIN-KEYWORD,chatgpt,AI-Services")

    # CF-Strict services (Cloudflare Bot Management)
    cf_strict = ["perplexity.ai", "mistral.ai", "poe.com"]
    for d in cf_strict:
        rules.append(f"DOMAIN-SUFFIX,{d},CF-Strict")

    # Dev AI
    dev_ai = ["cursor.com", "cursor.sh", "githubcopilot.com", "copilot.github.com", "replit.com"]
    for d in dev_ai:
        rules.append(f"DOMAIN-SUFFIX,{d},Dev-AI")

    # Social
    social = ["telegram.org", "t.me", "discord.com", "discordapp.com", "whatsapp.com", "x.com", "twimg.com"]
    for d in social:
        rules.append(f"DOMAIN-SUFFIX,{d},Social")

    # Streaming
    streaming = [
        "netflix.com", "nflxvideo.net", "disneyplus.com", "disney-plus.net",
        "youtube.com", "ytimg.com", "googlevideo.com",
        "hulu.com", "max.com", "primevideo.com", "tv.apple.com",
        "crunchyroll.com", "spotify.com", "scdn.co",
        "hbomax.com", "hbo.com",
    ]
    for d in streaming:
        rules.append(f"DOMAIN-SUFFIX,{d},Streaming")

    # Dev Services
    dev = [
        "github.com", "githubusercontent.com", "docker.com", "docker.io",
        "pypi.org", "npmjs.com", "vercel.com", "netlify.com", "supabase.com",
    ]
    for d in dev:
        rules.append(f"DOMAIN-SUFFIX,{d},Dev-Svc")

    # Web3
    web3 = ["binance.com", "binance.us", "coinbase.com", "opensea.io", "etherscan.io"]
    for d in web3:
        rules.append(f"DOMAIN-SUFFIX,{d},Web3")

    # Common Google — MUST come after service-specific rules (greedy keyword!)
    rules.append("DOMAIN-KEYWORD,google,Proxy")
    rules.append("DOMAIN-SUFFIX,google.com,Proxy")
    rules.append("DOMAIN-SUFFIX,googleapis.com,Proxy")

    # v1.3 收尾: Apple services — DIRECT for China App Store/iCloud, Proxy for international
    apple_direct = ["apple.com", "icloud.com", "icloud-content.com", "mzstatic.com",
                    "apple-cloudkit.com", "apple-dns.net"]
    for d in apple_direct:
        rules.append(f"DOMAIN-SUFFIX,{d},DIRECT")

    # v1.3 收尾: Microsoft services — DIRECT for China, Proxy for GitHub/CDN
    ms_direct = ["microsoft.com", "windowsupdate.com", "office.com", "office365.com",
                 "live.com", "msftauth.net", "msocsp.com"]
    for d in ms_direct:
        rules.append(f"DOMAIN-SUFFIX,{d},DIRECT")

    # v1.3 收尾: GitHub CDN — Proxy (GitHub raw/content often slow/blocked in China)
    rules.append("DOMAIN-SUFFIX,github.io,Dev-Svc")
    rules.append("DOMAIN-SUFFIX,githubassets.com,Dev-Svc")
    rules.append("DOMAIN-SUFFIX,github.dev,Dev-Svc")

    # v1.3 收尾: Cloudflare — Proxy (WARP/CF services need proxy)
    rules.append("DOMAIN-SUFFIX,cloudflare.com,Proxy")
    rules.append("DOMAIN-SUFFIX,cloudflareclient.com,Proxy")
    rules.append("DOMAIN-SUFFIX,workers.dev,Proxy")

    # v1.3 收尾: Tailscale — DIRECT (mesh VPN, direct connection is better)
    rules.append("DOMAIN-SUFFIX,tailscale.com,DIRECT")
    rules.append("DOMAIN-SUFFIX,tailscale.io,DIRECT")

    # v1.3 收尾: Steam — DIRECT for China store/downloads, Proxy for community
    rules.append("DOMAIN-SUFFIX,steamcontent.com,DIRECT")    # Steam CDN (China mirrors)
    rules.append("DOMAIN-SUFFIX,steampowered.com.chn,DIRECT")  # Steam China

    # v1.3 收尾: Line/Pixiv (common Japan services)
    rules.append("DOMAIN-SUFFIX,line.me,Social")
    rules.append("DOMAIN-SUFFIX,line-apps.com,Social")
    rules.append("DOMAIN-SUFFIX,pixiv.net,Proxy")

    # China direct
    rules.append("GEOIP,CN,DIRECT")

    # Final
    rules.append("MATCH,Proxy")

    return rules


def generate_shadowrocket_config(
    nodes: List[Dict],
    test_results: Optional[Dict[str, Dict]] = None,
    excluded_nodes: Optional[List[str]] = None,
) -> str:
    """Generate a Shadowrocket .conf file."""
    excluded = set(excluded_nodes or [])
    available = [n for n in nodes if n["name"] not in excluded]
    node_names = [n["name"] for n in available]

    lines = [
        "# Clash AI Proxy - Auto-generated Shadowrocket Configuration",
        "# Layered proxy group architecture for AI/streaming/social services",
        "# v1.1.0: lazy connections, priority sorting, IPv6 disabled, DoH fallback",
        "# Generated by clash-ai-proxy CLI",
        "",
        "[General]",
        "bypass-system-rules = true",
        "udp-policy-not-follow-proxy = false",
        "ipv6 = false",  # Disabled — many airports lack IPv6
        "dns-server = 223.5.5.5, 119.29.29.29, system",
        "fallback-dns-server = https://1.1.1.1/dns-query",  # DoH fallback for reliability
        "proxy-test-url = https://www.gstatic.com/generate_204",
        "udp-policy-not-follow-proxy = false",
        "",
        "[Proxy]",
        "",
    ]

    # Proxy groups
    for group_def in ARCHITECTURE["groups"]:
        group_nodes = _sort_nodes_by_priority(node_names, group_def)

        if test_results and group_def["services"]:
            service_excluded = set()
            for svc in group_def["services"]:
                for node_name, results in test_results.items():
                    svc_result = results.get("services", {}).get(svc, {})
                    if svc_result and not svc_result.get("reachable"):
                        service_excluded.add(node_name)
            group_nodes = [n for n in group_nodes if n not in service_excluded]

        if not group_nodes:
            group_nodes = node_names

        lines.append(f"# {group_def['name']} ({group_def.get('comment', group_def['type'])})")

        # Map group type to Shadowrocket types
        sr_type = group_def["type"]
        lazy_str = "" if group_def.get("lazy", True) else ""
        # Shadowrocket doesn't have a lazy directive, but we note it

        lines.append(
            f"{group_def['name']} = {sr_type}, "
            f"url={group_def['health_url']}, "
            f"interval={group_def['interval']}, "
            f"timeout=5000, {', '.join(group_nodes)}"
        )
        lines.append("")

    lines.append("[Proxy Group]")
    lines.append("")
    lines.append("[Rule]")
    lines.append("")

    # Reuse rule generation (without rule-providers for Shadowrocket compatibility)
    for rule in _generate_rules(use_rule_providers=False):
        lines.append(rule)

    lines.extend([
        "",
        "[Host]",
        "localhost = 127.0.0.1",
        "",
    ])

    return "\n".join(lines)
