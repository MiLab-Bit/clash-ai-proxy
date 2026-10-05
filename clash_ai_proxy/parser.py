"""
Clash subscription parser — reads existing Clash/mihomo YAML configs
and extracts node definitions for testing.
"""
import yaml
from typing import List, Dict, Optional


def parse_clash_config(config_path: str) -> List[Dict]:
    """
    Parse a Clash/mihomo YAML config and extract node (proxy) definitions.

    Args:
        config_path: Path to the .yaml config file

    Returns:
        List of node dicts with name, type, server, port, and full config
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    proxies = config.get("proxies", [])
    nodes = []
    for p in proxies:
        nodes.append({
            "name": p.get("name", ""),
            "type": p.get("type", ""),
            "server": p.get("server", ""),
            "port": p.get("port", 0),
            "_full": p,  # keep full config for generation
        })
    return nodes


def parse_shadowrocket_conf(conf_path: str) -> List[Dict]:
    """
    Parse a Shadowrocket .conf file and extract node definitions.
    Returns simplified node dicts.
    """
    nodes = []
    in_proxy = False

    with open(conf_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line == "[Proxy]":
                in_proxy = True
                continue
            if line.startswith("[") and line.endswith("]") and line != "[Proxy]":
                in_proxy = False
                continue

            if not in_proxy or not line or line.startswith("#"):
                continue

            # Parse node definition: name = type, server, port, ...
            if "=" in line:
                name, rest = line.split("=", 1)
                name = name.strip()
                rest = rest.strip()

                # Skip proxy group definitions (they contain 'url=' or keywords)
                if any(kw in rest for kw in ["url-test", "fallback", "select", "url="]):
                    continue

                parts = [p.strip() for p in rest.split(",")]
                if len(parts) >= 3:
                    nodes.append({
                        "name": name,
                        "type": parts[0],
                        "server": parts[1],
                        "port": int(parts[2]) if parts[2].isdigit() else 0,
                    })

    return nodes


def extract_servers(nodes: List[Dict]) -> Dict[str, tuple]:
    """Extract unique server:port pairs for TCP/TLS testing."""
    servers = {}
    for node in nodes:
        key = f"{node['name']}"
        if node["server"] and node["port"]:
            servers[key] = (node["server"], node["port"])
    return servers
