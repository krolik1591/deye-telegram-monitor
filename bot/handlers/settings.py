import logging
import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    SwitchInlineQueryChosenChat,
)

from db import mongodb
from menus.reply_menu import BTN_MENU, build_main_reply_kb
from menus.settings_menu import SettingsState, build_settings_menu
from services.master_service import MasterService

router = Router()


# ---------- unified /cancel for every SettingsState ----------

@router.message(
    StateFilter(
        SettingsState.waiting_for_yasno_group,
        SettingsState.waiting_for_channel_id,
    ),
    Command("cancel"),
)
async def cancel_any_fsm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")


# ---------- open menu ----------

@router.message(F.text == BTN_MENU)
async def open_settings(message: Message):
    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    text, kb = build_settings_menu(personal)
    await message.answer(text, reply_markup=kb)


# ---------- set yasno_group ----------

@router.callback_query(F.data == "settings:set_yasno_group")
async def start_set_yasno_group(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_yasno_group)
    await call.message.answer(
        "Введіть номер черги Ясно у форматі <b>X.Y</b> "
        "(наприклад, <code>25.1</code>).\n"
        "Для скасування напиши /cancel"
    )
    await call.answer()


@router.message(StateFilter(SettingsState.waiting_for_yasno_group))
async def receive_yasno_group(
    message: Message,
    state: FSMContext,
    master_service: MasterService,
):
    group = (message.text or "").strip()
    if not re.fullmatch(r"\d+\.\d+", group):
        await message.answer(
            "Невірний формат. Треба <code>X.Y</code> (наприклад, <code>25.1</code>). "
            "Спробуй ще раз або /cancel"
        )
        return

    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    if personal is None:
        await state.clear()
        await message.answer("Ви не зареєстровані 🤷")
        return

    await mongodb.set_yasno_group(personal.device_sn, group)
    await state.clear()

    # Populate the yasno collection for this group right away so the schedule
    # button works immediately. Usually a cache hit on YasnoClient (~ms).
    await master_service.new_yasno.prime_group(group)

    refreshed = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    await message.answer(
        f"✅ Групу Ясно оновлено: <b>{group}</b>",
        reply_markup=build_main_reply_kb(refreshed),
    )


# ---------- invite member ----------

@router.callback_query(F.data == "settings:invite")
async def invite_member(call: CallbackQuery):
    personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
    if personal is None:
        await call.answer("Ви не зареєстровані 🤷", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📤 Поділитись з другом",
            switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                query="invite",
                allow_user_chats=True,
            ),
        ),
    ]])

    await call.message.answer(
        "👥 <b>Запросити користувача</b>\n\n"
        "Натисни кнопку нижче — Telegram покаже твої чати, обери потрібний "
        "і запрошення полетить туди з красивою кнопкою «Приєднатись».",
        reply_markup=kb,
    )
    await call.answer()


# ---------- set channel_id ----------

@router.callback_query(F.data == "settings:set_channel_id")
async def start_set_channel_id(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_channel_id)
    await call.message.answer(
        "Введіть ID каналу (наприклад, <code>-1003824922225</code>).\n"
        "Переконайся, що бот доданий у канал як <b>адмін</b> з правом "
        "надсилати повідомлення.\n"
        "Для скасування напиши /cancel"
    )
    await call.answer()


@router.message(StateFilter(SettingsState.waiting_for_channel_id))
async def receive_channel_id(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not re.fullmatch(r"-100\d{9,13}", raw):
        await message.answer(
            "Невірний формат. Приклад: <code>-1003824922225</code>. "
            "Спробуй ще раз або /cancel"
        )
        return

    channel_id = int(raw)

    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    if personal is None:
        await state.clear()
        await message.answer("Ви не зареєстровані 🤷")
        return

    # Perms check: try to post + delete a test message. Only save on success.
    try:
        probe = await message.bot.send_message(
            chat_id=channel_id,
            text="✅ Бот під'єднано до каналу",
            disable_notification=True,
        )
    except Exception as e:
        await state.clear()
        await message.answer(
            f"❌ Не можу надіслати повідомлення в канал <code>{channel_id}</code>.\n"
            f"Переконайся, що бот доданий як адмін.\n\n"
            f"<i>{e}</i>"
        )
        return

    try:
        await message.bot.delete_message(chat_id=channel_id, message_id=probe.message_id)
    except Exception as e:
        logging.info(f"Can't delete probe message in {channel_id}: {e}")

    await mongodb.set_channel_id(personal.device_sn, channel_id)
    await state.clear()

    refreshed = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    await message.answer(
        f"✅ Канал збережено: <code>{channel_id}</code>",
        reply_markup=build_main_reply_kb(refreshed),
    )
