from datetime import datetime

import pytz

from types_.mixin_types import DeyeItem

LATEST_ITEMS_THRESHOLD = 60 * 60  # seconds


class TextService:
    def __init__(self, deye_item: DeyeItem):
        self.deye_item = deye_item

    def svitlo_on_text(self):
        return "☀️ Світло увімкнулось!"

    def svitlo_off_text(self):
        return "🌧 Світло вимкнено!"

    def duration_svitlo_on_text(self, time: int):
        return f"⏱️ Щасливі години: {self._format_time_pretty(time)}"

    def duration_svitlo_off_text(self, time: int):
        return f"⏱️ Тривалість відключення: {self._format_time_pretty(time)}"

    def energy_burned_text(self, soc_used: int):
        return f"🔋 Витрачено енергії: {soc_used}%"

    def grid_voltage_text(self):
        return f"⚡️ <b>Напруга мережі:</b> <i>{self.deye_item.grid_voltage} V</i>"

    def source_text(self):
        if self.deye_item.battery_power > 0:
            emoji, source = "🔋", "Батарея"
        else:
            emoji, source = "🌐", "Мережа"

        return f"{emoji} <b>Джерело:</b> <i>{source}</i>"

    def battery_text(self):
        soc = self.deye_item.soc
        battery_power = self.deye_item.battery_power
        abs_power = abs(battery_power)

        if soc >= 75:
            emoji = "🟢"
        elif soc >= 50:
            emoji = "🟡"
        else:
            emoji = "🔴"

        direction = "↓" if battery_power < 0 else "↑" if battery_power > 0 else ""

        return f"{emoji} <b>Рівень заряду:</b> <i>{soc}% ({abs_power}W {direction})</i>"

    def discharging_consumption_block(self):
        soc = self.deye_item.soc
        battery_power = self.deye_item.battery_power
        avg_batt_power = self.deye_item.average_battery_power

        current_time = self._time_to_discharge_text(soc, battery_power)
        avg_time = self._time_to_discharge_text(soc, avg_batt_power)

        return (
            "📊 <b>Споживання:</b>\n"
            f"    • Поточне: <i>{self._format_watt(battery_power)} → {current_time}</i>\n"
            f"    • Середнє: <i>{self._format_watt(avg_batt_power)} → {avg_time}</i>"
        )

    def time_to_charge_text(self):
        soc = self.deye_item.soc
        abs_power = abs(self.deye_item.battery_power)

        if soc >= 100:
            return ""

        if abs_power == 0:
            return "∞"

        remaining_energy = ((100 - soc) / 100) * self.deye_item.battery_capacity_kwh
        hours_to_full = remaining_energy / (abs_power / 1000)

        return f"\n    • <i>До повного заряду: {self._format_time_pretty(hours_to_full * 3600)}</i>"

    # TIME

    def updated_text(self):
        timestamp = self.deye_item.measured_at
        tz = pytz.timezone("Europe/Kyiv")
        local_time = datetime.fromtimestamp(timestamp, tz=tz)
        return f"🕐 <b>Оновлено:</b> <i>{local_time.strftime('%H:%M:%S')}</i>"

    @staticmethod
    def _format_time_pretty(seconds: float) -> str:
        """Format a duration (seconds) as "X год Y хв" or "Y хв"."""
        if seconds >= 3600:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h} год {m} хв"
        else:
            m = int(seconds // 60)
            return f"{m} хв"

    # HELPERS

    def _time_to_discharge_text(self, soc, battery_power):
        if battery_power <= 0:
            return "∞"

        available_energy = (soc / 100) * self.deye_item.battery_capacity_kwh
        hours_remaining = available_energy / (battery_power / 1000)
        return self._format_time_pretty(hours_remaining * 3600)

    @staticmethod
    def _format_watt(w):
        return f"{int(w)}W"
