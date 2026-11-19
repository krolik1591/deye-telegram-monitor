"""Small helpers shared by multiple handler modules."""

from db import mongodb


async def last_yasno_for(personal):
    """Latest ScheduleYasno for this personal's group, or None."""
    if personal is None or not personal.yasno_group:
        return None
    return await mongodb.get_last_yasno(personal.yasno_group)
