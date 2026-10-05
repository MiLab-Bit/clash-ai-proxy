#!/usr/bin/env python3
"""
Clash AI Proxy CLI — Test which proxy nodes can reach AI services
and generate an optimized layered proxy group architecture.

Usage:
  clash-ai test --proxy http://127.0.0.1:7897
  clash-ai test --proxy http://127.0.0.1:7897 --services chatgpt,gemini,claude
  clash-ai latency --config ~/.config/clash/config.yaml
  clash-ai generate --config ~/.config/clash/config.yaml --output optimized.yaml
  clash-ai full --config ~/.config/clash/config.yaml --proxy http://127.0.0.1:7897
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .services import SERVICES
from .tester import (
    test_service_through_proxy,
    test_node_latency_stability,
    classify_node,
)
from .parser import parse_clash_config, parse_shadowrocket_conf, extract_servers
from .generator import generate_clash_config, generate_shadowrocket_config


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def cmd_test(args):
    """Test which services are reachable through the current proxy."""
    proxy = args.proxy
    service_keys = args.services.split(",") if args.services else list(SERVICES.keys())

    print_header(f"Testing Services via {proxy}")

    print(f"{'Service':<25} {'Status':<8} {'Latency':<10} {'Verdict'}")
    print("-" * 65)

    reachable = 0
    total = len(service_keys)

    for key in service_keys:
        if key not in SERVICES:
            print(f"  Unknown service: {key}")
            continue

        result = test_service_through_proxy(proxy, key, timeout=args.timeout)
        status = result["status_code"] or "ERR"
        latency = f"{result['latency_ms']}ms" if result["latency_ms"] else "N/A"
        verdict = "REACHABLE" if result["reachable"] else f"BLOCKED ({result.get('error', status)})"
        marker = "+" if result["reachable"] else "x"
        print(f"{marker} {result['name']:<23} {str(status):<8} {latency:<10} {verdict}")
        if result["reachable"]:
            reachable += 1
        if result.get("notes") and not result["reachable"]:
            print(f"  -> Note: {result['notes']}")

    print(f"\nResult: {reachable}/{total} services reachable")


def cmd_latency(args):
    """Test latency/stability of all nodes in a config file."""
    config_path = args.config

    # Parse nodes
    if config_path.endswith(".yaml") or config_path.endswith(".yml"):
        nodes = parse_clash_config(config_path)
    else:
        nodes = parse_shadowrocket_conf(config_path)

    if not nodes:
        print("No nodes found in config file.")
        sys.exit(1)

    servers = extract_servers(nodes)

    print_header(f"Node Latency Test ({len(servers)} nodes)")

    print(f"{'Node':<15} {'Samples':<30} {'Avg':<8} {'Min':<8} {'Jitter':<8} {'Verdict'}")
    print("-" * 85)

    results = {}
    for name, (host, port) in servers.items():
        stability = test_node_latency_stability(host, port, samples=args.samples, timeout=5)
        results[name] = stability

        if stability["reachable"]:
            samples_str = str(stability["latencies"])
            jitter = stability["jitter_ms"]
            stable_marker = "stable" if stability["stable"] else "UNSTABLE"
            avg = f"{stability['avg_ms']}ms"
            mn = f"{stability['min_ms']}ms"
            jit = f"{jitter}ms"
            print(f"{name:<15} {samples_str:<30} {avg:<8} {mn:<8} {jit:<8} {stable_marker}")
        else:
            print(f"{name:<15} {'DEAD':<30} {'N/A':<8} {'N/A':<8} {'N/A':<8} DEAD NODE")

    # Summary
    print(f"\n--- Summary ---")
    stable = [n for n, r in results.items() if r["reachable"] and r["stable"]]
    unstable = [n for n, r in results.items() if r["reachable"] and not r["stable"]]
    dead = [n for n, r in results.items() if not r["reachable"]]

    print(f"Stable nodes:  {', '.join(stable) if stable else 'none'}")
    print(f"Unstable:      {', '.join(unstable) if unstable else 'none'}")
    print(f"Dead nodes:    {', '.join(dead) if dead else 'none'}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.json}")


def cmd_generate(args):
    """Generate optimized config from existing config + optional test results."""
    config_path = args.config

    if config_path.endswith(".yaml") or config_path.endswith(".yml"):
        nodes = parse_clash_config(config_path)
    else:
        nodes = parse_shadowrocket_conf(config_path)

    if not nodes:
        print("No nodes found in config.")
        sys.exit(1)

    # Load test results if provided
    test_results = None
    if args.test_results:
        with open(args.test_results) as f:
            test_results = json.load(f)

    # Excluded nodes
    excluded = args.exclude.split(",") if args.exclude else []

    print_header(f"Generating {'Clash' if args.format == 'clash' else 'Shadowrocket'} Config")

    if args.format == "clash":
        config_str = generate_clash_config(nodes, test_results, excluded)
    else:
        config_str = generate_shadowrocket_config(nodes, test_results, excluded)

    output = args.output or ("optimized.yaml" if args.format == "clash" else "optimized.conf")
    with open(output, "w", encoding="utf-8") as f:
        f.write(config_str)

    print(f"Generated: {output}")
    print(f"Nodes: {len(nodes)} total, {len(excluded)} excluded")
    if test_results:
        auto_excluded = sum(1 for r in test_results.values()
                           if r.get("classification") in ("dead", "region-blocked"))
        print(f"Auto-excluded (dead/blocked): {auto_excluded}")


def cmd_full(args):
    """Full pipeline: parse config -> test latency -> test services -> generate config."""
    config_path = args.config
    proxy = args.proxy

    # Step 1: Parse
    print_header("Step 1: Parsing config")
    if config_path.endswith((".yaml", ".yml")):
        nodes = parse_clash_config(config_path)
    else:
        nodes = parse_shadowrocket_conf(config_path)
    print(f"Found {len(nodes)} nodes")

    servers = extract_servers(nodes)

    # Step 2: Latency test
    print_header("Step 2: Testing node latency")
    test_results = {}
    for name, (host, port) in servers.items():
        stability = test_node_latency_stability(host, port, samples=3)
        test_results[name] = {"stability": stability}

        if stability["reachable"]:
            print(f"  {name}: avg {stability['avg_ms']}ms, jitter {stability['jitter_ms']}ms")
        else:
            print(f"  {name}: DEAD")

    # Step 3: Service test (via proxy — tests current node)
    print_header("Step 3: Testing service reachability")
    svc_keys = args.services.split(",") if args.services else ["chatgpt", "gemini", "claude", "telegram", "discord"]
    service_results = {}
    for key in svc_keys:
        result = test_service_through_proxy(proxy, key, timeout=args.timeout)
        service_results[key] = result
        status = "OK" if result["reachable"] else "FAIL"
        print(f"  {result['name']:<25} {status}")

    # Step 4: Classify nodes
    print_header("Step 4: Classification")
    for name in servers:
        stability = test_results[name]["stability"]
        classification = classify_node(stability, list(service_results.values()))
        test_results[name]["classification"] = classification
        print(f"  {name:<15} -> {classification}")

    # Step 5: Generate config
    print_header("Step 5: Generating optimized config")
    excluded = [n for n, r in test_results.items()
                if r.get("classification") in ("dead", "region-blocked")]
    if excluded:
        print(f"Auto-excluding: {', '.join(excluded)}")

    fmt = args.format or ("clash" if config_path.endswith((".yaml", ".yml")) else "shadowrocket")
    if fmt == "clash":
        config_str = generate_clash_config(nodes, test_results, excluded)
        output = args.output or "optimized.yaml"
    else:
        config_str = generate_shadowrocket_config(nodes, test_results, excluded)
        output = args.output or "optimized.conf"

    with open(output, "w", encoding="utf-8") as f:
        f.write(config_str)
    print(f"Saved: {output}")


def main():
    parser = argparse.ArgumentParser(
        prog="clash-ai",
        description="Test proxy nodes against AI services and generate optimized layered configs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clash-ai test --proxy http://127.0.0.1:7897
  clash-ai test --proxy http://127.0.0.1:7897 --services chatgpt,gemini
  clash-ai latency --config ~/.config/clash/config.yaml
  clash-ai generate --config config.yaml --output optimized.yaml
  clash-ai full --config config.yaml --proxy http://127.0.0.1:7897
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # test
    p_test = subparsers.add_parser("test", help="Test which services are reachable through proxy")
    p_test.add_argument("--proxy", required=True, help="Proxy URL (e.g., http://127.0.0.1:7897)")
    p_test.add_argument("--services", default=None, help="Comma-separated service keys (default: all)")
    p_test.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    p_test.set_defaults(func=cmd_test)

    # latency
    p_lat = subparsers.add_parser("latency", help="Test node latency and stability")
    p_lat.add_argument("--config", required=True, help="Path to Clash YAML or Shadowrocket .conf")
    p_lat.add_argument("--samples", type=int, default=5, help="Number of samples per node")
    p_lat.add_argument("--json", default=None, help="Save results to JSON file")
    p_lat.set_defaults(func=cmd_latency)

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate optimized config")
    p_gen.add_argument("--config", required=True, help="Path to existing config")
    p_gen.add_argument("--output", default=None, help="Output file path")
    p_gen.add_argument("--format", choices=["clash", "shadowrocket"], default="clash")
    p_gen.add_argument("--test-results", default=None, help="JSON file with test results")
    p_gen.add_argument("--exclude", default=None, help="Comma-separated node names to exclude")
    p_gen.set_defaults(func=cmd_generate)

    # full
    p_full = subparsers.add_parser("full", help="Full pipeline: test + generate")
    p_full.add_argument("--config", required=True, help="Path to existing config")
    p_full.add_argument("--proxy", required=True, help="Proxy URL for service testing")
    p_full.add_argument("--output", default=None, help="Output config path")
    p_full.add_argument("--services", default=None, help="Comma-separated services to test")
    p_full.add_argument("--timeout", type=int, default=10)
    p_full.add_argument("--format", choices=["clash", "shadowrocket"], default=None)
    p_full.set_defaults(func=cmd_full)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
