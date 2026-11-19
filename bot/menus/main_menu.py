from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.master_service import MasterService
from types_.mixin_types import DeyePersonal, ScheduleYasno


async def main_menu(master_service: MasterService, deye_personal: DeyePersonal, yasno: ScheduleYasno):
    deye_item = await master_service.deye_manager.get_item(deye_personal.device_sn)
    text = master_service.templates.bot_main_menu(deye_item, yasno)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔄 Оновити', callback_data="refresh")]
    ])

    return text.strip(), kb


def send_stats_to_channel_menu(message_id):
    text = "Пересилаємо?"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Переслати в канал",
                    callback_data=f"copy_to_channel_{message_id}"
                )
            ]
        ]
    )
    return text, kb