"""Aggregates every handler router for the dispatcher.

Order matters only when two routers could both match the same update; for us
they are disjoint (distinct commands, button texts, callback-data prefixes,
FSM states), so this order is mainly for readability.
"""

from .home import router as home_router
from .inline import router as inline_router
from .plugs import router as plugs_router
from .schedule import router as schedule_router
from .settings import router as settings_router
from .start import router as start_router
from .stats import router as stats_router

routers = [
    start_router,
    settings_router,
    stats_router,
    home_router,
    schedule_router,
    plugs_router,
    inline_router,
]
