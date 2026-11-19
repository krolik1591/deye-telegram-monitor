import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from db import mongodb
from menus.main_menu import send_stats_to_channel_menu
from menus.stats_menu import build_stats_menu
from services.image.main import (
    get_stats,
    get_stats_current_month,
    get_stats_last_days,
    get_stats_previous_month,
)

router = Router()


# ---------- submenu + period buttons ----------

@router.callback_query(F.data == "settings:stats")
async def open_stats_submenu(call: CallbackQuery):
    text, kb = build_stats_menu()
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "stats:7")
async def stats_7(call: CallbackQuery):
    await _render_stats_last(call, days=7)


@router.callback_query(F.data == "stats:14")
async def stats_14(call: CallbackQuery):
    await _render_stats_last(call, days=14)


@router.callback_query(F.data == "stats:month_current")
async def stats_month_current(call: CallbackQuery):
    personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
    if personal is None:
        await call.answer("Ви не зареєстровані 🤷", show_alert=True)
        return
    await call.answer("Готую зображення…")
    await _render_and_send(
        call.message,
        personal,
        lambda: get_stats_current_month(personal.device_sn),
        caption="📊 Поточний місяць",
    )


@router.callback_query(F.data == "stats:month_previous")
async def stats_month_previous(call: CallbackQuery):
    personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
    if personal is None:
        await call.answer("Ви не зареєстровані 🤷", show_alert=True)
        return
    await call.answer("Готую зображення…")
    await _render_and_send(
        call.message,
        personal,
        lambda: get_stats_previous_month(personal.device_sn),
        caption="📊 Минулий місяць",
    )


# ---------- legacy /stats CLI ----------

@router.message(Command("stats"))
async def stats_cli(message: Message):
    # cmd_example = "/stats 2026-2-1 7" yyyy-m-d duration
    try:
        _, date, duration = message.text.split(" ")
        year, month, day = map(int, date.split("-"))
        duration = int(duration)
    except Exception:
        await message.answer("Example: /stats yyyy-m-d duration")
        return

    personal = await mongodb.get_deye_personal_by_user_id(message.from_user.id)
    if personal is None:
        await message.answer("Ви не зареєстровані 🤷")
        return

    await _render_and_send(
        message,
        personal,
        lambda: get_stats(year, month, day, duration, personal.device_sn),
        caption="#stats",
    )


# ---------- forward last stats to channel ----------

@router.callback_query(F.data.startswith("copy_to_channel_"))
async def forward_handler(call: CallbackQuery):
    try:
        message_id = int(call.data.removeprefix("copy_to_channel_"))

        personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
        if not personal or personal.channel_id is None:
            await call.message.answer("У вас не вказаний channel_id 🤷")
            return

        await call.bot.copy_message(
            chat_id=personal.channel_id,
            from_chat_id=call.from_user.id,
            message_id=message_id,
        )
        await call.message.delete()
        await call.message.answer("Переслано!")
    except Exception as e:
        await call.message.delete()
        await call.message.answer(f"Error: {str(e)}")


# ---------- helpers ----------

async def _render_stats_last(call: CallbackQuery, days: int):
    personal = await mongodb.get_deye_personal_by_user_id(call.from_user.id)
    if personal is None:
        await call.answer("Ви не зареєстровані 🤷", show_alert=True)
        return
    await call.answer("Готую зображення…")
    await _render_and_send(
        call.message,
        personal,
        lambda: get_stats_last_days(personal.device_sn, days),
        caption=f"📊 Останні {days} днів",
    )


async def _render_and_send(message: Message, personal, build_coro, caption: str):
    """Run the stats-building coro, surface errors to the user, then post the image."""
    try:
        img_buffer = await build_coro()
    except ValueError as e:
        await message.answer(_friendly_stats_error(str(e)))
        return
    except Exception as e:
        logging.exception("stats render failed")
        await message.answer(
            "❌ Не вдалось побудувати статистику.\n"
            f"<code>{e}</code>"
        )
        return

    await _send_stats_image(message, personal, img_buffer, caption)


def _friendly_stats_error(raw: str) -> str:
    if raw.startswith("No svitlo events"):
        return (
            "ℹ️ У тебе ще немає історії по світлу.\n"
            "Дочекайся, поки бот збере хоч одну подію — тоді статистика буде доступна."
        )
    return f"❌ {raw}"


async def _send_stats_image(message: Message, personal, img_buffer, caption: str):
    try:
        photo_file = BufferedInputFile(img_buffer.getvalue(), filename="stats.png")
        msg = await message.answer_photo(photo=photo_file, caption=caption)
    except Exception as e:
        logging.exception("stats image send failed")
        await message.answer(
            "❌ Не вдалось відправити зображення.\n"
            f"<code>{e}</code>"
        )
        return

    if personal.channel_id is not None:
        text, kb = send_stats_to_channel_menu(msg.message_id)
        try:
            await message.answer(text, reply_markup=kb)
        except Exception as e:
            logging.warning(f"Can't send forward menu: {e}")
