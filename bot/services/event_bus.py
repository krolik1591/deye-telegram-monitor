"""
Typed, in-process async event bus.

Delivery contract:
  - at-most-once, in-process (events are NOT persisted or replayed)
  - dispatch is EXACT-type match: a handler for Base does not see subclass events
  - handlers for the same event type run SEQUENTIALLY, in registration order,
    unless the caller passes `concurrent=True`
  - errors in handlers are LOGGED and SWALLOWED; one failing handler does
    not stop the others
  - subscribe() returns a Subscription handle: call `.unsubscribe()` or use `with`
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, TypeVar

E = TypeVar("E")
Handler = Callable[[E], Awaitable[None]]
# `async def mw(event, call_next): ...` — call call_next() to continue the chain.
Middleware = Callable[[Any, Callable[[], Awaitable[None]]], Awaitable[None]]

log = logging.getLogger(__name__)


class Subscription:
    """Handle returned by EventBus.subscribe(). Supports `with sub: ...`."""

    def __init__(self, bus: "EventBus", event_type: type, handler: Handler[Any]):
        self._bus = bus
        self._event_type = event_type
        self._handler = handler
        self._active = True

    def unsubscribe(self) -> None:
        if not self._active:
            return
        handlers = self._bus._handlers.get(self._event_type, [])
        if self._handler in handlers:
            handlers.remove(self._handler)
        self._active = False

    def __enter__(self) -> "Subscription":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.unsubscribe()


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler[Any]]] = defaultdict(list)
        self._middlewares: list[Middleware] = []

    # ---------- registration ----------

    def subscribe(self, event_type: type[E], handler: Handler[E]) -> Subscription:
        self._handlers[event_type].append(handler)
        return Subscription(self, event_type, handler)

    def on(self, event_type: type[E]) -> Callable[[Handler[E]], Handler[E]]:
        """Decorator form:  @bus.on(SvitloOnEvent)"""
        def deco(fn: Handler[E]) -> Handler[E]:
            self.subscribe(event_type, fn)
            return fn
        return deco

    def use(self, middleware: Middleware) -> None:
        """Append a middleware. The first-registered one wraps outermost."""
        self._middlewares.append(middleware)

    # ---------- dispatch ----------

    async def emit(
        self,
        event: Any,
        *,
        concurrent: bool = False,
        timeout: float | None = None,
    ) -> None:
        handlers = list(self._handlers.get(type(event), ()))
        if not handlers:
            return

        async def dispatch() -> None:
            if concurrent:
                results = await asyncio.gather(
                    *(self._run(h, event, timeout) for h in handlers),
                    return_exceptions=True,
                )
                for h, r in zip(handlers, results):
                    if isinstance(r, BaseException):
                        log.error(
                            "Handler %s failed for %s",
                            h.__qualname__, type(event).__name__,
                            exc_info=r,
                        )
            else:
                for h in handlers:
                    try:
                        await self._run(h, event, timeout)
                    except Exception:
                        log.exception(
                            "Handler %s failed for %s",
                            h.__qualname__, type(event).__name__,
                        )

        await self._chain(0, event, dispatch)

    async def _chain(
        self,
        index: int,
        event: Any,
        dispatch: Callable[[], Awaitable[None]],
    ) -> None:
        if index >= len(self._middlewares):
            await dispatch()
            return
        mw = self._middlewares[index]
        await mw(event, lambda: self._chain(index + 1, event, dispatch))

    @staticmethod
    async def _run(handler: Handler[Any], event: Any, timeout: float | None) -> None:
        if timeout is None:
            await handler(event)
        else:
            await asyncio.wait_for(handler(event), timeout=timeout)