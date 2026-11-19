from typing import Optional

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from types_.mixin_types import DeyePersonal


class SettingsState(StatesGroup):
    waiting_for_yasno_group = State()
    waiting_for_channel_id = State()


def build_settings_menu(personal: Optional[DeyePersonal]):
    group = personal.yasno_group if personal and personal.yasno_group else "не вказано"
    plug = personal.plug_service if personal and personal.plug_service else "не налаштовано"
    channel = (
        f"<code>{personal.channel_id}</code>"
        if personal and personal.channel_id is not None
        else "не вказано"
    )

    text = (
        "<b>⚙️ Меню</b>\n\n"
        f"⚡ <i>Група Ясно:</i> <b>{group}</b>\n"
        f"📢 <i>Канал:</i> {channel}\n"
        f"🔌 <i>Plug service:</i> <b>{plug}</b>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Змінити групу Ясно",
                callback_data="settings:set_yasno_group",
            )],
            [InlineKeyboardButton(
                text="📢 Встановити канал",
                callback_data="settings:set_channel_id",
            )],
            [InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="settings:stats",
            )],
            [InlineKeyboardButton(
                text="👥 Запросити користувача",
                callback_data="settings:invite",
            )],
        ]
    )
    return text, kb
