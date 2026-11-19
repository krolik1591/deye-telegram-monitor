import copy
import datetime
import time
from dataclasses import dataclass, field
from typing import List, Optional, TypedDict

from types_.mongo_mixin import MongoDataclassMixin
from types_.types import DeyeData, ScheduleRaw
from utils._time import tz_now

@dataclass
class ScheduleYasno(MongoDataclassMixin):
    group: str
    updates: list[ScheduleRaw]
    date_str: str




@dataclass
class SvitloItem(MongoDataclassMixin):
    device_sn: int
    svitlo: bool
    soc: Optional[int] = 0

    timestamp: int = field(default_factory=lambda: int(tz_now().timestamp()))
    date_str: str = field(default_factory=lambda: tz_now().strftime('%Y-%m-%d'))


class Alerts(TypedDict):
    soc: int
    triggered: bool
    emoji: str


DEFAULT_ALERTS: list[Alerts] = [
    {"soc": 75, "triggered": False, "emoji": "☘️"},
    {"soc": 50, "triggered": False, "emoji": "⚠️"},
    {"soc": 25, "triggered": False, "emoji": "‼️"},
]


@dataclass
class BasicDeyePersonal:
    """Minimal fields required to seed a new DeyePersonal from .env.

    `password` must already be SHA-256 hex (lowercase) — the Deye API expects
    the hashed form. Hashing is done in `settings.dotenv_config`.
    """
    user_ids: List[int]
    app_id: int
    app_secret: str
    email: str
    password: str
    device_sn: int
    battery_capacity_kwh: int


@dataclass
class DeyePersonal(MongoDataclassMixin):
    user_ids: List[int]
    app_id: int     #   66666666666666
    app_secret: str #   "63gr6g5464fb29dfdwf51684654"
    email: str      #   "sanya@gmail.com"
    password: str   #   SHA-256 hex (lowercase)
    device_sn: int  #   6666666666
    battery_capacity_kwh: int
    alerts: list[Alerts]

    yasno_group: Optional[str] = None       # e.g. "25.1"; None → no Yasno for this user
    channel_id: Optional[int] = None        # e.g. -100... ; None → no channel pins/edits/forwards
    plug_service: Optional[str] = None      # e.g. "tapo_local"; None → no plug control

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    @classmethod
    def from_basic(
        cls,
        basic: BasicDeyePersonal,
        alerts: Optional[list[Alerts]] = None,
    ) -> "DeyePersonal":
        return cls(
            user_ids=basic.user_ids,
            app_id=basic.app_id,
            app_secret=basic.app_secret,
            email=basic.email,
            password=basic.password,
            device_sn=basic.device_sn,
            battery_capacity_kwh=basic.battery_capacity_kwh,
            alerts=alerts if alerts is not None else copy.deepcopy(DEFAULT_ALERTS),
        )

@dataclass
class Plug(MongoDataclassMixin):
    ip: str
    nickname: str
    device_on: bool

    watcher_enabled: bool = True
    last_sync: int = int(time.time())
    is_online: bool = True



@dataclass
class DeyeItem:
    device_sn: int
    battery_capacity_kwh: int   # 5 KWH

    soc: int
    battery_power: int
    grid_voltage: float
    measured_at: int
    average_battery_power: int
    deye_data: List[DeyeData]


@dataclass
class SvitloOnEvent:
    item: DeyeItem
    prev_event: SvitloItem

@dataclass
class SvitloOffEvent:
    item: DeyeItem
    prev_event: SvitloItem

@dataclass
class PowerAlertEvent:
    item: DeyeItem
    emoji: str


@dataclass
class NewScheduleEvent:
    schedule: ScheduleYasno


@dataclass
class UpdateScheduleEvent:
    schedule: ScheduleYasno

