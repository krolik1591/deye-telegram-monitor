"""
Probe Deye API rate limits to estimate how many users one deployment can serve.

HOW
    1. Make sure at least one DeyePersonal exists in Mongo.
    2. Edit USER_ID / BURST_SIZE / DELAY_MS below.
    3. From the `bot/` dir:  python tests/deye_rate_limit.py

WHAT IT MEASURES
    We fire BURST_SIZE back-to-back requests from ONE Deye account and
    count successes vs. errors. From the sustained throughput we derive:

        max_users = (requests per minute) × 5

    because each user polls once every 5 min = 0.2 req/min per user.

CAVEATS
    - This measures the limit of ONE Deye account (one email login).
      Deye may apply limits per-account OR per-IP; if per-account is the
      binding constraint, running the bot with N DIFFERENT Deye accounts
      scales linearly; if per-IP, the number stays flat.
    - A short burst reveals the "burst cap" (≈ RPS peak). A real
      sustained rate could be lower — Deye may allow, e.g., 60/min
      peak but only 500/hour sustained. For a conservative estimate,
      divide the measured rpm by 2.
    - Errors with HTTP 200 + body `{"msg": "..."}` are still counted as
      a failure; Deye sometimes signals quota exhaustion in the body.
"""

import asyncio
import time
from typing import Any

import aiohttp

from clients.deye_client import DeyeAuthError, DeyeClient
from db import mongodb


USER_ID = 357108179       # whose DeyePersonal to use
BURST_SIZE = 10           # how many requests to fire
DELAY_MS = 0              # pause between requests (0 = as fast as possible)
POLL_INTERVAL_MIN = 5     # each user's poll period in minutes

# Deye's "success" sentinel in the JSON body. Anything else = problem.
OK_CODES = {1_000_000, 1000000}


async def main() -> None:
    personal = await mongodb.get_deye_personal_by_user_id(USER_ID)
    if personal is None:
        print(f"No DeyePersonal for user_id={USER_ID}")
        return

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        client = DeyeClient(personal, session)

        print(f"Warming up token for {personal.email}…")
        try:
            await client.get_device_info()
        except DeyeAuthError:
            # expected on first call — token refresh handled internally
            pass
        except Exception as e:
            print(f"Warm-up failed: {e!r}")
            return

        print(f"Firing burst: {BURST_SIZE} requests, delay={DELAY_MS}ms")
        print("-" * 72)

        results: list[tuple[int, str, int]] = []
        start = time.time()
        rate_limited = False

        for i in range(BURST_SIZE):
            req_start = time.time()
            status = "ok"
            try:
                data = await client.get_device_info()
                if not _is_success(data):
                    status = f"api_code={data.get('code')} msg={data.get('msg')!r}"
            except DeyeAuthError as e:
                status = f"auth_error: {e}"
            except aiohttp.ClientResponseError as e:
                status = f"http_{e.status}"
            except asyncio.TimeoutError:
                status = "timeout"
            except Exception as e:
                status = f"{type(e).__name__}: {e}"

            latency_ms = int((time.time() - req_start) * 1000)
            results.append((i + 1, status, latency_ms))
            print(f"[{i + 1:3d}] {status[:60]:60s}  {latency_ms:4d} ms")

            if _looks_like_rate_limit(status):
                print(
                    f"\n⛔ Looks rate-limited after {i + 1} requests "
                    f"({time.time() - start:.1f}s elapsed)"
                )
                rate_limited = True
                break

            if DELAY_MS:
                await asyncio.sleep(DELAY_MS / 1000)

        elapsed = time.time() - start
        successes = sum(1 for _, s, _ in results if s == "ok")

        print("-" * 72)
        print(f"Elapsed:   {elapsed:.1f}s")
        print(f"Attempted: {len(results)}")
        print(f"Succeeded: {successes}")
        if successes and elapsed > 0:
            rps = successes / elapsed
            rpm = rps * 60
            rph = rps * 3600
            per_user_rpm = 1 / POLL_INTERVAL_MIN
            max_users_burst = int(rpm / per_user_rpm)
            max_users_conservative = int((rpm / 2) / per_user_rpm)
            print()
            print(f"Throughput: {rps:.1f} req/s  ≈  {rpm:.0f} req/min  ≈  {rph:.0f} req/h")
            print(f"Assuming each user polls every {POLL_INTERVAL_MIN} min "
                  f"({per_user_rpm:.2f} req/min per user):")
            print(f"  burst-ceiling estimate:   max_users ≈ {max_users_burst}")
            print(f"  conservative (÷2 safety): max_users ≈ {max_users_conservative}")
        else:
            print("No successes — can't derive throughput.")

        if rate_limited:
            print("\n👉 Error patterns to watch above help you distinguish per-IP vs per-account limits.")


def _is_success(data: dict) -> bool:
    """Deye returns `code` as str or int; sometimes it's absent entirely."""
    code = data.get("code")
    if code is None:
        return True
    try:
        return int(str(code)) in OK_CODES
    except (TypeError, ValueError):
        return False


def _looks_like_rate_limit(status: str) -> bool:
    low = status.lower()
    return any(
        marker in low
        for marker in (
            "429",
            "too many",
            "rate",
            "limit",
            "quota",
            "throttle",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
