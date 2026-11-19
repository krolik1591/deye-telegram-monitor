from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_stats_menu():
    text = "<b>📊 Статистика</b>\n\nОбери період:"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 За 7 днів", callback_data="stats:7")],
            [InlineKeyboardButton(text="📅 За 14 днів", callback_data="stats:14")],
            [InlineKeyboardButton(text="🗓 Поточний місяць", callback_data="stats:month_current")],
            [InlineKeyboardButton(text="🗓 Минулий місяць", callback_data="stats:month_previous")],
        ]
    )
    return text, kb
