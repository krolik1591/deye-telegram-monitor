"""First-start seeding.

If the `deye_personal` collection is empty on startup and `.env` has the
bootstrap vars, this creates the initial DeyePersonal so the admin doesn't
have to run tests/add_deye_personal.py by hand.
"""

import logging
from typing import Optional

from db import mongodb
from settings.dotenv_config import dotenv_config
from types_.mixin_types import DeyePersonal


async def ensure_first_personal() -> Optional[DeyePersonal]:
    existing = await mongodb.get_all_deye_personals()
    if existing:
        return None

    basic = dotenv_config.deye_basic
    if basic is None:
        logging.warning(
            "deye_personal is empty and .env has no bootstrap vars — "
            "add a personal manually via tests/add_deye_personal.py"
        )
        return None

    personal = DeyePersonal.from_basic(basic)
    created = await mongodb.create_deye_personal(personal)
    logging.info(
        f"Bootstrap: seeded initial DeyePersonal "
        f"(device_sn={created.device_sn}, user_ids={created.user_ids})"
    )
    return created
