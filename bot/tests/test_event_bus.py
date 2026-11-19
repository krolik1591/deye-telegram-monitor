"""
Smoke tests for services.event_bus.EventBus.

Run from the `bot/` directory:
    pip install pytest
    pytest tests/test_event_bus.py

(No pytest-asyncio needed — each test wraps asyncio.run.)
"""

import asyncio
import logging
from dataclasses import dataclass

from services.event_bus import EventBus


@dataclass
class EventA:
    value: int


@dataclass
class EventB:
    value: int


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_dispatch_by_type():
    bus = EventBus()
    got_a, got_b = [], []

    async def ha(e): got_a.append(e.value)
    async def hb(e): got_b.append(e.value)

    bus.subscribe(EventA, ha)
    bus.subscribe(EventB, hb)

    _run(bus.emit(EventA(1)))
    _run(bus.emit(EventB(2)))

    assert got_a == [1]
    assert got_b == [2]


def test_ordering_sequential():
    bus = EventBus()
    order: list[str] = []

    async def h1(e): order.append("h1")
    async def h2(e): order.append("h2")
    async def h3(e): order.append("h3")

    bus.subscribe(EventA, h1)
    bus.subscribe(EventA, h2)
    bus.subscribe(EventA, h3)

    _run(bus.emit(EventA(0)))
    assert order == ["h1", "h2", "h3"]


def test_error_isolation(caplog):
    bus = EventBus()
    seen: list[str] = []

    async def good(e): seen.append("good")
    async def bad(e):  raise RuntimeError("boom")
    async def also_good(e): seen.append("also_good")

    bus.subscribe(EventA, good)
    bus.subscribe(EventA, bad)
    bus.subscribe(EventA, also_good)

    with caplog.at_level(logging.ERROR, logger="services.event_bus"):
        _run(bus.emit(EventA(0)))

    assert seen == ["good", "also_good"]
    assert any("bad" in r.message for r in caplog.records)


def test_unsubscribe_handle():
    bus = EventBus()
    seen: list[int] = []

    async def h(e): seen.append(e.value)
    sub = bus.subscribe(EventA, h)

    _run(bus.emit(EventA(1)))
    sub.unsubscribe()
    _run(bus.emit(EventA(2)))

    assert seen == [1]


def test_unsubscribe_context_manager():
    bus = EventBus()
    seen: list[int] = []

    async def h(e): seen.append(e.value)

    with bus.subscribe(EventA, h):
        _run(bus.emit(EventA(1)))
    _run(bus.emit(EventA(2)))

    assert seen == [1]


def test_decorator_registration():
    bus = EventBus()
    seen: list[int] = []

    @bus.on(EventA)
    async def _(e):
        seen.append(e.value)

    _run(bus.emit(EventA(42)))
    assert seen == [42]


def test_concurrent_mode_runs_in_parallel():
    bus = EventBus()
    order: list[str] = []

    async def slow(e):
        await asyncio.sleep(0.05)
        order.append("slow")

    async def fast(e):
        order.append("fast")

    bus.subscribe(EventA, slow)
    bus.subscribe(EventA, fast)

    _run(bus.emit(EventA(0), concurrent=True))
    assert order == ["fast", "slow"]


def test_middleware_wraps_dispatch():
    bus = EventBus()
    trace: list[str] = []

    async def logging_mw(event, call_next):
        trace.append(f"before:{type(event).__name__}")
        await call_next()
        trace.append(f"after:{type(event).__name__}")

    async def h(e): trace.append("handler")

    bus.use(logging_mw)
    bus.subscribe(EventA, h)

    _run(bus.emit(EventA(0)))
    assert trace == ["before:EventA", "handler", "after:EventA"]


def test_handler_timeout_continues_chain(caplog):
    bus = EventBus()
    seen: list[str] = []

    async def hangs(e):
        await asyncio.sleep(1)
        seen.append("hangs_done")

    async def quick(e):
        seen.append("quick_done")

    bus.subscribe(EventA, hangs)
    bus.subscribe(EventA, quick)

    with caplog.at_level(logging.ERROR, logger="services.event_bus"):
        _run(bus.emit(EventA(0), timeout=0.05))

    assert "quick_done" in seen
    assert "hangs_done" not in seen


def test_no_handler_is_a_noop():
    bus = EventBus()
    # just shouldn't raise
    _run(bus.emit(EventA(0)))


def test_exact_type_match_only():
    """Dispatch is by exact type — handlers for parent classes don't fire."""
    bus = EventBus()

    @dataclass
    class Child(EventA):
        extra: str = ""

    seen_parent, seen_child = [], []

    async def on_parent(e): seen_parent.append(e)
    async def on_child(e):  seen_child.append(e)

    bus.subscribe(EventA, on_parent)
    bus.subscribe(Child, on_child)

    _run(bus.emit(Child(value=1, extra="x")))

    assert seen_parent == []     # <-- exact match only
    assert len(seen_child) == 1
