"""
Node tester — tests which proxy nodes can reach AI/streaming/social services.
The core tool for diagnosing dead nodes, region-blocked nodes, and routing issues.
"""
import time
import socket
import ssl
import json
import statistics
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    requests = None

from .services import SERVICES


def test_node_tcp_tls(host: str, port: int, timeout: int = 5) -> Optional[float]:
    """Test raw TCP + TLS handshake latency to a node server (ms)."""
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        elapsed = (time.time() - start) * 1000
        ssl_sock.close()
        return round(elapsed)
    except Exception:
        return None


def test_service_through_proxy(
    proxy_url: str,
    service_key: str,
    timeout: int = 10,
    user_agent: str = "Mozilla/5.0",
) -> Dict:
    """
    Test if a service is reachable through the given proxy.
    Returns dict with: reachable, status_code, latency_ms, error
    """
    svc = SERVICES[service_key]
    url = svc["health_url"]
    expect = svc["expect_status"]

    proxies = {"http": proxy_url, "https": proxy_url}
    headers = {"User-Agent": user_agent}

    try:
        if requests is None:
            raise ImportError("requests library required. Install with: pip install requests")

        start = time.time()
        resp = requests.get(url, proxies=proxies, headers=headers, timeout=timeout, allow_redirects=False)
        elapsed = round((time.time() - start) * 1000)

        reachable = resp.status_code in expect
        return {
            "service": service_key,
            "name": svc["name"],
            "reachable": reachable,
            "status_code": resp.status_code,
            "latency_ms": elapsed,
            "error": None,
            "notes": svc.get("notes", ""),
        }
    except requests.exceptions.ConnectTimeout:
        return {"service": service_key, "name": svc["name"], "reachable": False,
                "status_code": None, "latency_ms": None, "error": "Connection timeout (node may be dead)",
                "notes": svc.get("notes", "")}
    except requests.exceptions.SSLError as e:
        return {"service": service_key, "name": svc["name"], "reachable": False,
                "status_code": None, "latency_ms": None, "error": f"SSL error: {e}",
                "notes": svc.get("notes", "")}
    except Exception as e:
        return {"service": service_key, "name": svc["name"], "reachable": False,
                "status_code": None, "latency_ms": None, "error": str(e),
                "notes": svc.get("notes", "")}


def test_all_services(
    proxy_url: str,
    service_keys: Optional[List[str]] = None,
    timeout: int = 10,
) -> List[Dict]:
    """Test all (or specified) services through the proxy."""
    keys = service_keys or list(SERVICES.keys())
    results = []
    for key in keys:
        results.append(test_service_through_proxy(proxy_url, key, timeout))
    return results


def test_node_latency_stability(
    host: str,
    port: int,
    samples: int = 5,
    timeout: int = 5,
) -> Dict:
    """
    Test node latency stability over multiple samples.
    Reveals jitter — a node averaging 400ms but with spikes to 1900ms is worse
    than a stable 600ms node.
    """
    latencies = []
    for _ in range(samples):
        lat = test_node_tcp_tls(host, port, timeout)
        if lat is not None:
            latencies.append(lat)

    if not latencies:
        return {"reachable": False, "latencies": [], "avg_ms": None,
                "min_ms": None, "max_ms": None, "jitter_ms": None}

    avg = round(statistics.mean(latencies))
    jitter = max(latencies) - min(latencies)
    return {
        "reachable": True,
        "latencies": latencies,
        "avg_ms": avg,
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "jitter_ms": jitter,
        "stable": jitter < (avg * 0.5),  # jitter < 50% of avg = stable
    }


def classify_node(stability: Dict, service_results: List[Dict]) -> str:
    """
    Classify a node based on its test results.
    Returns one of: 'excellent', 'good', 'unstable', 'dead', 'region-blocked'
    """
    if not stability.get("reachable"):
        return "dead"

    if not stability.get("stable") and stability.get("jitter_ms", 0) > 1000:
        return "unstable"

    reachable_count = sum(1 for r in service_results if r.get("reachable"))
    total = len(service_results)

    if reachable_count == total:
        return "excellent" if stability["avg_ms"] < 500 else "good"
    elif reachable_count == 0:
        return "region-blocked"
    else:
        return "good" if reachable_count > total / 2 else "unstable"
