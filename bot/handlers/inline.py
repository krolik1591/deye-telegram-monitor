from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from db import mongodb

router = Router()


@router.inline_query()
async def inline_invite(query: InlineQuery):
    """Answers the chat-picker invoked by the 👥 Запросити button.

    The button pre-fills `@botname invite`; we don't filter on `query.query`
    text — we just answer once per call with a personal, uncached result."""
    personal = await mongodb.get_deye_personal_by_user_id(query.from_user.id)
    if personal is None:
        await query.answer([], cache_time=0, is_personal=True)
        return

    token = await mongodb.create_invite(personal.device_sn)
    me = await query.bot.get_me()
    deep_link = f"https://t.me/{me.username}?start=invite_{token}"

    article = InlineQueryResultArticle(
        id=f"invite_{token}",
        title="⚡ Запросити до Electric Bot",
        description="Надішли це повідомлення — друг отримає кнопку приєднання",
        input_message_content=InputTextMessageContent(
            message_text=(
                "⚡️ <b>Приєднуйся до Electric Bot!</b>\n\n"
                "Слідкуй за світлом, графіком Ясно і керуй розетками 🔌"
            ),
            parse_mode="HTML",
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Приєднатись", url=deep_link),
        ]]),
    )

    await query.answer([article], cache_time=0, is_personal=True)
