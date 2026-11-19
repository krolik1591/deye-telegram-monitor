import logging
import re

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from db import mongodb
from handlers._shared import last_yasno_for
from menus.main_menu import main_menu
from menus.reply_menu import BTN_STATUS
from services.master_service import MasterService

router = Router()


@router.message(F.text == BTN_STATUS)
async def status_handler(message: Message, master_service: MasterService):
    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    yasno = await last_yasno_for(personal)
    text, kb = await main_menu(master_service, personal, yasno)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "refresh")
async def refresh_status(call: CallbackQuery, master_service: MasterService):
    personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
    yasno = await last_yasno_for(personal)
    text, kb = await main_menu(master_service, personal, yasno)

    if _normalize(call.message.text) == _normalize(text):
        logging.info("No refresh! Texts the same")
        await call.answer("✅ Це актуальна інфа", show_alert=True)
        return

    await call.message.edit_text(text, reply_markup=kb)


def _normalize(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n\s+", "\n", t)
    t = re.sub(r"\n{2,}", "\n\n", t)
    return t.strip()
