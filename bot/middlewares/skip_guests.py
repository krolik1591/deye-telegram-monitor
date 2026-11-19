import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from settings.electric_members import electric_members


class SkipGuestsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        if user_id not in electric_members.available_members:
            if not _is_invite_bypass(event):
                logging.info(f"Skip guest user_id={user_id}")
                return

        result = await handler(event, data)

        try:
            await event.answer()
        except Exception:
            pass

        return result


def _is_invite_bypass(event: Union[Message, CallbackQuery]) -> bool:
    """Non-members are allowed through iff they're arriving via /start invite_<token>."""
    if isinstance(event, Message) and event.text:
        return event.text.startswith("/start invite_")
    return False
