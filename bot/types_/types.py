from typing import TypedDict, List, Literal


class RawDeyeItem(TypedDict):
    key: str
    unit: str
    value: int

class DeyeData(TypedDict):
    itemList: List[RawDeyeItem]
    time: int


class ScheduleSlot(TypedDict):
    start: int
    end: int
    type: Literal["Definite", "NotPlanned"]


class ScheduleDay(TypedDict):
    date: str
    slots: list[ScheduleSlot]
    status: Literal["ScheduleApplies", "WaitingForSchedule", "EmergencyShutdowns"]


class ScheduleRaw(TypedDict):
    today: ScheduleDay
    tomorrow: ScheduleDay
    updatedOn: str
