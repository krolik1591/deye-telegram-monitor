from typing import TYPE_CHECKING, Optional

from services.texts import templates as t
from services.texts.yasno_texts import get_n_line_schedule

if TYPE_CHECKING:
    from services.master_service import MasterService

from services.texts.text_service import TextService
from types_.mixin_types import DeyeItem, ScheduleYasno


class TemplatesService:
    text_service: Optional[TextService] = None
    schedule_line: Optional[str] = None


    def __init__(self, master_service: 'MasterService'):
        self.master_service = master_service

    def init_text_service(self, deye_item: DeyeItem, yasno: ScheduleYasno):
        self.text_service = TextService(deye_item)
        self.schedule_line = get_n_line_schedule(yasno)

    def bot_main_menu(self, deye_item: DeyeItem, yasno: ScheduleYasno):
        self.init_text_service(deye_item, yasno)

        if deye_item.battery_power < 0:
            template = t.CHARGING_TEMPLATE
        else:
            template = t.DISCHARGING_TEMPLATE

        return template.format(
            source=self.text_service.source_text(),
            battery=self.text_service.battery_text(),
            consumption=self.text_service.discharging_consumption_block(),
            time_to_charge=self.text_service.time_to_charge_text(),
            updated=self.text_service.updated_text(),

            grid_voltage=self.text_service.grid_voltage_text(),

            schedule=self.schedule_line,
        )

    def hata_svitlo_on(self, time_on, soc_used):
        return t.HATA_SVITLO_ON_TEMPLATE.format(
            svitlo_on=self.text_service.svitlo_on_text(),
            duration_svitlo_off=self.text_service.duration_svitlo_off_text(time_on),
            energy_burned=self.text_service.energy_burned_text(soc_used=soc_used),

            grid_voltage=self.text_service.grid_voltage_text(),

            schedule=self.schedule_line,
        )

    def hata_svitlo_off(self, time_on):
        return t.HATA_SVITLO_OFF_TEMPLATE.format(
            svitlo_off=self.text_service.svitlo_off_text(),
            duration_svitlo_on=self.text_service.duration_svitlo_on_text(time_on),
            consumption=self.text_service.discharging_consumption_block(),

            grid_voltage=self.text_service.grid_voltage_text(),

            schedule=self.schedule_line,
        )

    def channel_svitlo_on(self, time_off: int):
        return t.CHANNEL_SVITLO_ON_TEMPLATE.format(
            svitlo_on=self.text_service.svitlo_on_text(),
            duration_svitlo_off=self.text_service.duration_svitlo_off_text(time_off),

            grid_voltage=self.text_service.grid_voltage_text(),

            schedule=self.schedule_line,
        )

    def channel_svitlo_off(self, time_on: int):
        return t.CHANNEL_SVITLO_OFF_TEMPLATE.format(
            svitlo_off=self.text_service.svitlo_off_text(),
            duration_svitlo_on=self.text_service.duration_svitlo_on_text(time_on),

            grid_voltage=self.text_service.grid_voltage_text(),

            schedule=self.schedule_line,
        )

    def hata_power_alert_template(self, soc: int, emoji: str):
        return t.HATA_POWER_ALERT_TEMPLATE.format(
            soc=soc,
            emoji=emoji,
            consumption=self.text_service.discharging_consumption_block(),

            schedule=self.schedule_line,
        )
