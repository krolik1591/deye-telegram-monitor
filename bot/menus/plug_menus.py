from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from types_.mixin_types import Plug


def plugs_menu(plugs: List[Plug]):
    text = f"Список ваших розеток:"

    plug_btns = []
    for plug in plugs:
        emoji = "🟢" if plug.device_on else "🔴"
        emoji = emoji if plug.is_online else "OFFLINE"
        btn_text = f"{plug.nickname}: {emoji}"
        callback = f"plug_ip|{plug.ip}"
        plug_btns.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        *plug_btns,
    ])

    return text, kb


def plug_refactored_settings(plug: Plug):
    text = (
        f"Device: {plug.nickname}\n"
        f"Auto-control: {plug.watcher_enabled}\n"
        f"Is turn on: {plug.device_on}"
    )
    kb = _plug_settings_kb(plug)
    return text, kb


def _plug_settings_kb(plug: Plug):
    watcher_state = "ON" if plug.watcher_enabled else "OFF"
    emoji = "👈"

    if plug.device_on:
        current_state = "on"
        turn_on_text = f"TURN ON {emoji}"
        turn_off_text = f"TURN OFF"

    else:
        current_state = "off"
        turn_on_text = f"TURN ON"
        turn_off_text = f"TURN OFF {emoji}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _create_btn(turn_on_text, f"plug_turn_on|{plug.ip}|{current_state}"),
            _create_btn(turn_off_text, f"plug_turn_off|{plug.ip}|{current_state}")
        ],
        [_create_btn(f"Auto-control: {watcher_state}", f"plug_watcher_state|{plug.ip}")],
    ])


def _create_btn(text, callback) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)
