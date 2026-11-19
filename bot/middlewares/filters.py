from typing import Any, Union

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from db import mongodb


class FilterHasPlugService(Filter):
    """Pass only if the user's DeyePersonal has a non-None `plug_service`."""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        personal = await mongodb.get_deye_personal_by_user_id(event.from_user.id)
        return bool(personal) and personal.plug_service is not None
