from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from db import mongodb
from menus.plug_menus import plugs_menu, plug_refactored_settings
from menus.reply_menu import BTN_PLUGS
from middlewares.filters import FilterHasPlugService
from services.master_service import MasterService
from services.plugs_service import DeviceStateWarning

router = Router()

# Gate every plug entry point on the user having a plug_service configured.
router.message.filter(FilterHasPlugService())
router.callback_query.filter(FilterHasPlugService())


@router.message(F.text == BTN_PLUGS)
async def plugs(message: Message, master_service: MasterService):
    all_plugs = await master_service.plugs.get_and_update_plugs()

    text, kb = plugs_menu(all_plugs)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith('plug_ip|'))
async def plug_ip(call: CallbackQuery, master_service: MasterService, ip: str = None) -> None:
    if not ip:
        ip = call.data.split('|')[1]

    plug = await mongodb.get_plug_by_ip(ip)
    if not plug.is_online:
        text = "Device offline"
        await call.answer(text, show_alert=True)
        return

    text, kb = plug_refactored_settings(plug)
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith('plug_turn_on|'))
async def plug_turn_on(call: CallbackQuery, master_service: MasterService) -> None:
    _, ip, prev_state = call.data.split('|')

    if prev_state == "on":
        text = f"Device already {prev_state}"
        await call.answer(text, show_alert=True)
        return

    try:
        await master_service.plugs.enable_plug(ip)
    except DeviceStateWarning as e:
        await call.answer(str(e), show_alert=True)
        return
    except Exception as e:
        await call.answer(str(e), show_alert=True)
        return

    text = "Device enabled!"
    await call.answer(text, show_alert=True)
    await plug_ip(call, master_service)


@router.callback_query(F.data.startswith('plug_turn_off|'))
async def plug_turn_off(call: CallbackQuery, master_service: MasterService) -> None:
    _, ip, prev_state = call.data.split('|')

    if prev_state == "off":
        text = f"Device already {prev_state}"
        await call.answer(text, show_alert=True)
        return

    try:
        await master_service.plugs.disable_plug(ip)
    except DeviceStateWarning as e:
        await call.answer(str(e), show_alert=True)
        return
    except Exception as e:
        await call.answer(str(e), show_alert=True)
        return

    text = "Device disabled!"
    await call.answer(text, show_alert=True)
    await plug_ip(call, master_service)


@router.callback_query(F.data.startswith('plug_watcher_state|'))
async def plug_watcher_state(call: CallbackQuery, master_service: MasterService) -> None:
    ip = call.data.split('|')[1]

    plug = await mongodb.get_plug_by_ip(ip)
    await mongodb.update_watcher_enable_state(ip, not plug.watcher_enabled)

    await call.answer("✅ Watcher state changed!", show_alert=True)

    await plug_ip(call, master_service)
