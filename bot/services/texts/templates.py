CHARGING_TEMPLATE = """
<b>⚡️ ПОТОЧНИЙ СТАН СИСТЕМИ</b>

{source}
{battery}{time_to_charge}
{grid_voltage}

{schedule}

{updated}
"""

DISCHARGING_TEMPLATE = """
<b>⚡️ ПОТОЧНИЙ СТАН СИСТЕМИ</b>

{source}
{battery}

{consumption}
{grid_voltage}

{schedule}

{updated}
"""

CHANNEL_SVITLO_ON_TEMPLATE = """
{svitlo_on}
{duration_svitlo_off}

{grid_voltage}

{schedule}
"""

CHANNEL_SVITLO_OFF_TEMPLATE = """
{svitlo_off}
{duration_svitlo_on}

{grid_voltage}

{schedule}
"""

HATA_SVITLO_ON_TEMPLATE = """
{svitlo_on}
{duration_svitlo_off}
{energy_burned}

{grid_voltage}

{schedule}
"""

HATA_SVITLO_OFF_TEMPLATE = """
{svitlo_off} Перевірте бойлер та кондиціонери 🐱‍
{duration_svitlo_on}

{consumption}

{grid_voltage}

{schedule}
"""

HATA_POWER_ALERT_TEMPLATE = """
{emoji} Увага! Поточний рівень заряду {soc}%

{consumption}

{schedule}
"""

