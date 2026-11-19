from aiogram import F, Router
from aiogram.types import Message

from db import mongodb
from handlers._shared import last_yasno_for
from menus.reply_menu import BTN_SCHEDULE
from services.texts.yasno_texts import get_schedule_text

router = Router()


@router.message(F.text == BTN_SCHEDULE)
async def schedule_handler(message: Message):
    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    yasno = await last_yasno_for(personal)
    await message.answer(get_schedule_text(yasno))
