import logging
from datetime import timedelta
from typing import Optional

import aiohttp

from utils._time import tz_now


class YasnoClient:
    def __init__(
        self,
        region_id: int = 25,
        dso_id: int = 902,
        base_url: str = "https://app.yasno.ua/api/blackout-service/public",
    ):
        self.url = (
            f"{base_url}/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"
        )

        self._data: Optional[dict] = None
        self._last_fetch_time = None

        self._timeout = aiohttp.ClientTimeout(total=10)

    async def fetch(self):
        now = tz_now()

        need_fetch = (
            self._data is None
            or self._last_fetch_time is None
            or now - self._last_fetch_time > timedelta(minutes=5)
        )

        if not need_fetch:
            return self._data

        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(self.url) as resp:
                    resp.raise_for_status()
                    self._data = await resp.json()
                    self._last_fetch_time = now

        except Exception:
            logging.exception("Yasno fetch error")

            if self._data is None:
                raise

            return self._data

        return self._data

    async def get_group(self, group: str):
        data = await self.fetch()
        return data[group]