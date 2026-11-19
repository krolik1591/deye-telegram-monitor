from typing import Optional

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from types_.mixin_types import DeyePersonal


BTN_STATUS = "🏠 Хата"
BTN_SCHEDULE = "💡 Світло"
BTN_PLUGS = "🔌 Розетки"
BTN_MENU = "⚙️ Меню"


def build_main_reply_kb(personal: Optional[DeyePersonal]) -> ReplyKeyboardMarkup:
    """Reply keyboard shown under the pinned welcome message.

    - Row 1: 🏠 Хата (always) + 💡 Світло (if yasno_group) + 🔌 Розетки (if plug_service)
    - Row 2: ⚙️ Меню (always)
    """
    row1: list[KeyboardButton] = [KeyboardButton(text=BTN_STATUS)]
    if personal and personal.yasno_group:
        row1.append(KeyboardButton(text=BTN_SCHEDULE))
    if personal and personal.plug_service:
        row1.append(KeyboardButton(text=BTN_PLUGS))

    rows = [row1, [KeyboardButton(text=BTN_MENU)]]

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )
