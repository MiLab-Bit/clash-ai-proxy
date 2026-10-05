"""
Service definitions for AI/Web3/streaming/etc.
Each service has the domains to test and the expected behavior.

Health check URL tips:
- Not all services have /generate_204 endpoints — use gstatic for generic tests
- For AI services, prefer service-specific URLs (e.g., chatgpt.com/cdn-cgi/trace)
  to detect nodes that are "dead for this service but alive for others"
"""

SERVICES = {
    # ========== AI Services ==========
    "chatgpt": {
        "name": "ChatGPT",
        "category": "ai",
        "health_url": "https://chatgpt.com/cdn-cgi/trace",
        "domains": ["chatgpt.com", "openai.com", "oaistatic.com", "oaiusercontent.com"],
        "expect_status": [200],
        "notes": (
            "Some nodes return 000 (dead) — they can't reach OpenAI backend even though "
            "they work for other services. Known: HK nodes often dead for OpenAI while "
            "sharing the same exit IP as working USA nodes. "
            "JP-01 reported as 'no network connection' on iOS app."
        ),
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "category": "ai",
        "health_url": "https://claude.ai",
        "domains": ["claude.ai", "anthropic.com"],
        "expect_status": [200, 301, 302, 403],
        "notes": "403 from curl = Cloudflare anti-bot. Browser usually works fine.",
    },
    "gemini": {
        "name": "Google Gemini",
        "category": "ai",
        "health_url": "https://www.gstatic.com/generate_204",
        "domains": [
            "gemini.google.com", "generativelanguage.googleapis.com",
            "aistudio.google.com", "notebooklm.google.com",
            # Auxiliary domains — WITHOUT these, Gemini app shows blank screen
            "accounts.google.com", "www.gstatic.com", "ssl.gstatic.com",
            "lh3.googleusercontent.com", "play.google.com",
        ],
        "expect_status": [200, 204],
        "notes": (
            "Gemini iOS app checks IP + GPS + SIM + Apple ID region. "
            "Proxy alone may not be enough on mobile — disable Location Services "
            "for the Google/Gemini app and set region to US. "
            "LU (Luxembourg) FranTech IPs partially blocked by Google. "
            "gemini.google.com/generate_204 is unstable (intermittent disconnects) — "
            "use gstatic.com/generate_204 instead."
        ),
    },
    "grok": {
        "name": "Grok (xAI)",
        "category": "ai",
        "health_url": "https://x.ai",
        "domains": ["x.ai", "grok.com"],
        "expect_status": [200],
    },
    "perplexity": {
        "name": "Perplexity",
        "category": "ai",
        "health_url": "https://perplexity.ai",
        "domains": ["perplexity.ai"],
        "expect_status": [200, 403],
        "notes": "Cloudflare Bot Management — may need residential IP.",
    },
    "mistral": {
        "name": "Mistral AI",
        "category": "ai",
        "health_url": "https://mistral.ai",
        "domains": ["mistral.ai"],
        "expect_status": [200, 403],
        "notes": "Cloudflare Bot Management — may need residential IP.",
    },
    "cohere": {
        "name": "Cohere",
        "category": "ai",
        "health_url": "https://cohere.com",
        "domains": ["cohere.com"],
        "expect_status": [200],
    },
    "character": {
        "name": "Character.ai",
        "category": "ai",
        "health_url": "https://character.ai",
        "domains": ["character.ai"],
        "expect_status": [200],
    },
    "poe": {
        "name": "Poe",
        "category": "ai",
        "health_url": "https://poe.com",
        "domains": ["poe.com"],
        "expect_status": [200, 403],
        "notes": "Cloudflare Bot Management.",
    },

    # ========== Streaming ==========
    "netflix": {
        "name": "Netflix",
        "category": "streaming",
        "health_url": "https://www.netflix.com",
        "domains": ["netflix.com", "nflxvideo.net"],
        "expect_status": [200],
    },
    "youtube": {
        "name": "YouTube",
        "category": "streaming",
        "health_url": "https://www.youtube.com",
        "domains": ["youtube.com", "ytimg.com", "googlevideo.com"],
        "expect_status": [200],
    },
    "disney": {
        "name": "Disney+",
        "category": "streaming",
        "health_url": "https://www.disneyplus.com",
        "domains": ["disneyplus.com", "disney-plus.net"],
        "expect_status": [200],
    },
    "hbo": {
        "name": "HBO Max",
        "category": "streaming",
        "health_url": "https://www.max.com",
        "domains": ["max.com", "hbomax.com"],
        "expect_status": [200],
    },
    "primevideo": {
        "name": "Prime Video",
        "category": "streaming",
        "health_url": "https://www.primevideo.com",
        "domains": ["primevideo.com"],
        "expect_status": [200],
    },
    "crunchyroll": {
        "name": "Crunchyroll",
        "category": "streaming",
        "health_url": "https://www.crunchyroll.com",
        "domains": ["crunchyroll.com"],
        "expect_status": [200],
    },
    "spotify": {
        "name": "Spotify",
        "category": "streaming",
        "health_url": "https://www.spotify.com",
        "domains": ["spotify.com", "scdn.co"],
        "expect_status": [200],
    },

    # ========== Social ==========
    "telegram": {
        "name": "Telegram",
        "category": "social",
        "health_url": "https://telegram.org",
        "domains": ["telegram.org", "t.me"],
        "expect_status": [200],
    },
    "discord": {
        "name": "Discord",
        "category": "social",
        "health_url": "https://discord.com/api/v1/ping",
        "domains": ["discord.com", "discordapp.com"],
        "expect_status": [200, 204, 400, 404],
    },
    "twitter": {
        "name": "Twitter/X",
        "category": "social",
        "health_url": "https://x.com",
        "domains": ["x.com", "twimg.com"],
        "expect_status": [200],
    },
    "whatsapp": {
        "name": "WhatsApp",
        "category": "social",
        "health_url": "https://www.whatsapp.com",
        "domains": ["whatsapp.com", "whatsapp.net"],
        "expect_status": [200],
    },

    # ========== Dev ==========
    "github": {
        "name": "GitHub",
        "category": "dev",
        "health_url": "https://github.com",
        "domains": ["github.com", "githubusercontent.com"],
        "expect_status": [200],
    },
    "docker": {
        "name": "Docker Hub",
        "category": "dev",
        "health_url": "https://hub.docker.com",
        "domains": ["docker.com", "docker.io"],
        "expect_status": [200],
    },
    "npm": {
        "name": "npm Registry",
        "category": "dev",
        "health_url": "https://registry.npmjs.org",
        "domains": ["npmjs.com", "registry.npmjs.org"],
        "expect_status": [200],
    },
    "pypi": {
        "name": "PyPI",
        "category": "dev",
        "health_url": "https://pypi.org",
        "domains": ["pypi.org", "pythonhosted.org"],
        "expect_status": [200],
    },
    "vercel": {
        "name": "Vercel",
        "category": "dev",
        "health_url": "https://vercel.com",
        "domains": ["vercel.com", "vercel.app"],
        "expect_status": [200],
    },

    # ========== Web3 ==========
    "binance": {
        "name": "Binance",
        "category": "web3",
        "health_url": "https://www.binance.com/bapi/finance/footer/v1/public/footer/list",
        "domains": ["binance.com", "binance.me"],
        "expect_status": [200],
    },
    "coinbase": {
        "name": "Coinbase",
        "category": "web3",
        "health_url": "https://www.coinbase.com",
        "domains": ["coinbase.com"],
        "expect_status": [200, 403],
        "notes": "Cloudflare Bot Management — curl may get 403, browser works.",
    },
    "opensea": {
        "name": "OpenSea",
        "category": "web3",
        "health_url": "https://opensea.io",
        "domains": ["opensea.io"],
        "expect_status": [200],
    },

    # ========== AI Developer Tools ==========
    "cursor": {
        "name": "Cursor",
        "category": "dev-ai",
        "health_url": "https://cursor.com",
        "domains": ["cursor.sh", "cursor.com"],
        "expect_status": [200],
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "category": "dev-ai",
        "health_url": "https://github.com/features/copilot",
        "domains": ["copilot.github.com"],
        "expect_status": [200],
    },
    "huggingface": {
        "name": "Hugging Face",
        "category": "dev-ai",
        "health_url": "https://huggingface.co",
        "domains": ["huggingface.co"],
        "expect_status": [200],
    },
    "replit": {
        "name": "Replit",
        "category": "dev-ai",
        "health_url": "https://replit.com",
        "domains": ["replit.com"],
        "expect_status": [200],
    },
}

# Service categories with recommended strategy group type
CATEGORIES = {
    "ai": {
        "recommended_type": "fallback",
        "description": (
            "AI services need stable nodes — use fallback to auto-switch on failure. "
            "Critical: health check URL should be service-specific (not gstatic) "
            "to detect nodes that are 'dead for this AI but alive for others'."
        ),
    },
    "streaming": {
        "recommended_type": "fallback",
        "description": "Streaming needs consistent exit IP — fallback prevents mid-session switches",
    },
    "social": {
        "recommended_type": "fallback",
        "description": "Social/messaging needs reliability — fallback auto-selects best available",
    },
    "dev": {
        "recommended_type": "fallback",
        "description": "Dev tools need reliability — fallback ensures connectivity",
    },
    "dev-ai": {
        "recommended_type": "url-test",
        "description": "Dev AI tools (Cursor/Copilot) — low stakes, url-test is fine",
    },
    "web3": {
        "recommended_type": "fallback",
        "description": "Web3 exchanges need stable nodes with good geo-blocking compatibility",
    },
}

# Known dead-node patterns by airport (community-contributed)
# Add your findings here: {airport: {node: {service: "reason"}}}
KNOWN_DEAD_NODES = {
    "lyhyclloud": {
        "HK-01": {"chatgpt": "Returns 000 — routing to OpenAI backend broken"},
        "HK-02": {"chatgpt": "Returns 000 — same as HK-01"},
        "JP-01": {"chatgpt": "iOS app shows 'no network connection'"},
        "Warp-CF": {"all": "WireGuard dead node — TCP never responds"},
        "UK-01": {"all": "High jitter (446ms+ avg), unstable for all services"},
        "UK-02": {"all": "Same as UK-01"},
        "LU-01": {"gemini": "FranTech IP range partially blocked by Google"},
        "LU-02": {"gemini": "Same FranTech range as LU-01"},
    },
}
