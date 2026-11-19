import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from db import mongodb
from menus.reply_menu import build_main_reply_kb
from settings.electric_members import electric_members

router = Router()

INVITE_PREFIX = "invite_"


@router.message(Command("start"))
async def command_start(message: Message, command: CommandObject):
    # /start invite_<token> → attach this user to the token's device_sn
    if command.args and command.args.startswith(INVITE_PREFIX):
        await _handle_invite(message, command.args.removeprefix(INVITE_PREFIX))

    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)

    welcome = (
        "<b>👋 Привіт!</b>\n\n"
        "Користуйся кнопками нижче, щоб керувати ботом."
    )
    msg = await message.answer(welcome, reply_markup=build_main_reply_kb(personal))

    try:
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            disable_notification=True,
        )
    except Exception as e:
        logging.info(f"Can't pin welcome: {e}")


async def _handle_invite(message: Message, token: str) -> None:
    device_sn = await mongodb.consume_invite(token)
    if device_sn is None:
        await message.answer("❌ Недійсне або прострочене посилання.")
        return

    await mongodb.add_user_to_device(device_sn, message.from_user.id)
    # Refresh the in-memory allowlist so SkipGuestsMiddleware starts letting
    # this user through on subsequent messages.
    await electric_members.update()
    await message.answer(f"✅ Вас додано до пристрою <code>{device_sn}</code>!")
