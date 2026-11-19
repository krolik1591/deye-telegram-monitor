"""
Parallel version of the Deye rate-limit probe.

Fires N requests concurrently (via asyncio.gather) and waits for every one
to come back. This answers "what happens if the bot slams the API all at
once" — the peak-concurrency case.

HOW
    1. Edit USER_ID / N below.
    2. From the `bot/` dir:  python tests/deye_rate_limit_parallel.py

DIFF FROM deye_rate_limit.py
    - That one is sequential (one at a time) → measures the sustainable RPS.
    - This one is parallel (all at once) → measures max concurrent capacity
      of one account + one aiohttp ClientSession.

BE CAREFUL
    N=1000 is a lot. A friendly API usually returns either HTTP 429 or a
    `code != 1_000_000` body long before 1000 succeed. If your account
    gets locked out, wait 24 h and try again with a smaller N.
"""

import asyncio
import statistics
import time
from collections import Counter

import aiohttp

from clients.deye_client import DeyeAuthError, DeyeClient
from db import mongodb


USER_ID = 357108179
N = 100                         # how many concurrent requests to fire
POLL_INTERVAL_MIN = 5            # per-user poll period for capacity math
TOTAL_TIMEOUT_SEC = 60           # aiohttp overall timeout per request
OK_CODES = {1_000_000, 1000000}  # Deye's success sentinel


async def main() -> None:
    personal = await mongodb.get_deye_personal_by_user_id(USER_ID)
    if personal is None:
        print(f"No DeyePersonal for user_id={USER_ID}")
        return

    timeout = aiohttp.ClientTimeout(total=TOTAL_TIMEOUT_SEC)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        client = DeyeClient(personal, session)

        print(f"Warming up token for {personal.email}…")
        try:
            await client.get_device_info()
        except DeyeAuthError:
            pass
        except Exception as e:
            print(f"Warm-up failed: {e!r}")
            return

        print(f"Firing {N} requests concurrently and awaiting all…\n")

        start = time.time()
        results = await asyncio.gather(
            *(_one(client, i) for i in range(N)),
            return_exceptions=False,
        )
        elapsed = time.time() - start

        _report(results, elapsed)


async def _one(client: DeyeClient, idx: int) -> tuple[str, int]:
    """One attempt → (status_label, latency_ms)."""
    t0 = time.time()
    status = "ok"
    try:
        data = await client.get_device_info()
        if not _is_success(data):
            status = f"api code={data.get('code')} msg={data.get('msg')!r}"
    except DeyeAuthError as e:
        status = f"auth_error: {e}"
    except aiohttp.ClientResponseError as e:
        status = f"http_{e.status}"
    except asyncio.TimeoutError:
        status = "timeout"
    except Exception as e:
        status = f"{type(e).__name__}: {e}"

    return status, int((time.time() - t0) * 1000)


def _is_success(data: dict) -> bool:
    """Deye returns `code` as str or int; sometimes it's absent entirely."""
    code = data.get("code")
    if code is None:
        # no error indicator → assume success (mirrors device_runtime's assumption)
        return True
    try:
        return int(str(code)) in OK_CODES
    except (TypeError, ValueError):
        return False


def _report(results: list[tuple[str, int]], elapsed: float) -> None:
    print("=" * 72)
    print(f"All {len(results)} requests finished in {elapsed:.2f}s")
    print("=" * 72)

    # Group statuses: "ok" vs error buckets
    buckets: Counter[str] = Counter()
    for status, _ in results:
        buckets[_bucket(status)] += 1

    successes = buckets.get("ok", 0)
    print(f"Succeeded: {successes}/{len(results)}  "
          f"({successes / len(results) * 100:.1f}%)")

    if buckets:
        print("\nBreakdown:")
        for label, count in buckets.most_common():
            bar = "█" * min(40, int(count / len(results) * 40))
            print(f"  {label:25s} {count:5d}  {bar}")

    # Latency distribution across ALL attempts (successes + errors)
    latencies = [lat for _, lat in results]
    if latencies:
        print("\nLatency across all attempts (ms):")
        print(f"  min    {min(latencies):5d}")
        print(f"  median {int(statistics.median(latencies)):5d}")
        print(f"  p95    {_pct(latencies, 95):5d}")
        print(f"  max    {max(latencies):5d}")

    # Capacity math — same as sequential script
    if successes and elapsed > 0:
        rps = successes / elapsed
        rpm = rps * 60
        per_user_rpm = 1 / POLL_INTERVAL_MIN
        print()
        print(f"Effective throughput under {N}-way parallelism:")
        print(f"  {rps:.1f} req/s ≈ {rpm:.0f} req/min")
        print(f"At 1 req / {POLL_INTERVAL_MIN} min per user → "
              f"max_users ≈ {int(rpm / per_user_rpm)}")

    # Hint about rate-limit detection
    rate_signals = sum(buckets[b] for b in buckets if _looks_like_rate_limit(b))
    if rate_signals:
        print(f"\n⛔ {rate_signals} responses look rate-limited "
              f"(status contains 'rate', 'limit', '429', 'quota'…).")
        print("   The sequential tests/deye_rate_limit.py will show where the "
              "cliff is more clearly.")


def _bucket(status: str) -> str:
    """Collapse detailed statuses into small labels for the breakdown."""
    if status == "ok":
        return "ok"
    if status.startswith("api code="):
        # keep the code so quota signals stay visible
        return status.split(" msg=")[0]
    if status.startswith("http_"):
        return status
    if status.startswith("auth_error"):
        return "auth_error"
    if status == "timeout":
        return "timeout"
    return status.split(":")[0]  # ExceptionType


def _pct(values: list[int], pct: int) -> int:
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100) * (len(s) - 1)))))
    return s[k]


def _looks_like_rate_limit(label: str) -> bool:
    low = label.lower()
    return any(
        marker in low
        for marker in ("429", "rate", "limit", "quota", "throttle", "too many")
    )


if __name__ == "__main__":
    asyncio.run(main())
