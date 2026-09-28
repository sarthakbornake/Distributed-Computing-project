import argparse
import asyncio
import csv
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

GATEWAY_URL = "http://127.0.0.1:8000"
AUTH_URL = "http://127.0.0.1:8001"

VALID_COUNTRY = "IN"
BAD_COUNTRY = "US"

def percentile(values, p):
    if not values:
        return 0.0
    return float(np.percentile(values, p))

async def get_token(client, role="admin", trust=0.95):
    resp = await client.post(
        f"{AUTH_URL}/token",
        json={"user_id": f"bench-{random.randint(1, 10_000_000)}",
              "role": role,
              "device_trust": trust},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

async def one_request(client, mode, request_type, token, role_mismatch_token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # All requests target /api/data so role-based access is normally valid.
    # Attack types alter either role/endpoint or dynamic context.
    if request_type == "role_mismatch":
        # Create a guest token for a protected endpoint.
        if role_mismatch_token is None:
            raise RuntimeError("role_mismatch_token is required")
        headers["Authorization"] = f"Bearer {role_mismatch_token}"

    if request_type == "context_mismatch":
        headers["X-Geo-Country"] = BAD_COUNTRY
        headers["X-Device-Trust"] = "0.95"
        # Use an allowed role, but a bad dynamic context.

    if request_type == "valid":
        headers["X-Geo-Country"] = VALID_COUNTRY
        headers["X-Device-Trust"] = "0.95"

    params = {"mode": mode}
    start = time.perf_counter()
    try:
        resp = await client.get(f"{GATEWAY_URL}/api/data", params=params, headers=headers)
        status = resp.status_code
        ok = status < 400
    except Exception:
        status = 599
        ok = False
    latency_ms = (time.perf_counter() - start) * 1000.0

    return {
        "latency_ms": latency_ms,
        "status": status,
        "allowed": int(ok),
        "request_type": request_type,
        "mode": mode,
    }

async def benchmark_mode(mode, requests_count, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    records = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Warm-up
        token = await get_token(client, role="admin", trust=0.95)
        guest_token = await get_token(client, role="guest", trust=0.95)
        for _ in range(20):
            await one_request(client, mode, "valid", token, guest_token)

        # Main run
        request_types = (
            ["valid"] * int(requests_count * 0.70)
            + ["role_mismatch"] * int(requests_count * 0.15)
            + ["context_mismatch"] * (requests_count - int(requests_count * 0.70) - int(requests_count * 0.15))
        )
        random.shuffle(request_types)

        async def limited(rt):
            async with semaphore:
                return await one_request(client, mode, rt, token, guest_token)

        wall_start = time.perf_counter()
        results = await asyncio.gather(*(limited(rt) for rt in request_types))
        wall_duration_s = time.perf_counter() - wall_start
        records.extend(results)

    latencies = [r["latency_ms"] for r in records]
    blocked = [r for r in records if not r["allowed"]]
    context = [r for r in records if r["request_type"] == "context_mismatch"]
    role = [r for r in records if r["request_type"] == "role_mismatch"]

    throughput = len(records) / max(wall_duration_s, 1e-9)

    summary = {
        "mode": mode,
        "requests": len(records),
        "mean_latency_ms": mean(latencies) if latencies else 0.0,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "blocked": len(blocked),
        "overall_block_rate_pct": 100.0 * len(blocked) / max(len(records), 1),
        "context_attack_block_rate_pct": 100.0 * sum(1 for r in context if not r["allowed"]) / max(len(context), 1),
        "role_attack_block_rate_pct": 100.0 * sum(1 for r in role if not r["allowed"]) / max(len(role), 1),
        "approx_rps": throughput,
    }
    return summary

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=10000)
    parser.add_argument("--concurrency", type=int, default=100)
    args = parser.parse_args()

    results = []
    for mode in ("noac", "rbac", "abac"):
        print(f"Running {mode}...")
        result = await benchmark_mode(mode, args.requests, args.concurrency)
        results.append(result)
        print(result)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = RESULTS_DIR / f"summary_{timestamp}.csv"

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved: {output}")

if __name__ == "__main__":
    asyncio.run(main())
