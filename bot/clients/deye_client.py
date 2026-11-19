import hashlib
from typing import Dict, Any

import aiohttp

from db import mongodb
from metrics import OBSERVER_METRICS
from utils._time import tz_now


class DeyeAuthError(Exception):
    pass


class DeyeClient:
    BASE_URL = "https://eu1-developer.deyecloud.com/v1.0"
    DEVICE_HISTORY_URL = f"{BASE_URL}/device/history"
    TOKEN_URL = f"{BASE_URL}/account/token"

    def __init__(self, deye_personal, session: aiohttp.ClientSession):
        self.deye_personal = deye_personal
        self._session = session

    async def get_device_info(self) -> Dict[str, Any]:
        payload = self._build_history_payload()

        data = await self._post(
            self.DEVICE_HISTORY_URL,
            json=payload,
            headers=self._auth_header()
        )

        if self._is_token_invalid(data):
            await self._refresh_and_store_tokens()
            raise DeyeAuthError("Access token refreshed. Retry request.")

        return data

    async def _post(self, url: str, **kwargs) -> Dict[str, Any]:
        async with self._session.post(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def _get_access_tokens(self) -> Dict[str, str]:
        url = f"{self.TOKEN_URL}?appId={self.deye_personal.app_id}"

        payload = {
            "appSecret": self.deye_personal.app_secret,
            "email": self.deye_personal.email,
            "password": self.deye_personal.password,
        }

        async with self._session.post(url, json=payload) as response:
            response.raise_for_status()
            data = await response.json()

        return {
            "access_token": data["accessToken"],
            "refresh_token": data["refreshToken"],
        }

    async def _refresh_and_store_tokens(self) -> None:
        tokens = await self._get_access_tokens()

        self.deye_personal.access_token = tokens["access_token"]
        self.deye_personal.refresh_token = tokens["refresh_token"]

        await mongodb.set_access_tokens(
            self.deye_personal.device_sn,
            tokens["access_token"],
            tokens["refresh_token"]
        )

    def _auth_header(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.deye_personal.access_token}"
        }

    def _build_history_payload(self) -> Dict[str, Any]:
        today = tz_now().strftime('%Y-%m-%d')

        return {
            "deviceSn": self.deye_personal.device_sn,
            "startAt": today,
            "endAt": today,
            "granularity": 1,
            "measurePoints": OBSERVER_METRICS,
        }

    def _is_token_invalid(self, data: Dict[str, Any]) -> bool:
        return data.get("msg") == "auth invalid token"

    def _convert_password(self):
        return hashlib.sha256(
            self.deye_personal.password.encode('utf-8')
        ).hexdigest().lower()


class DeyeClientManager:
    def __init__(self):
        self._clients: dict[int, DeyeClient] = {}

        timeout = aiohttp.ClientTimeout(total=10)
        self._session = aiohttp.ClientSession(timeout=timeout)

    def get_client(self, personal) -> DeyeClient:
        if personal.device_sn not in self._clients:
            self._clients[personal.device_sn] = DeyeClient(
                personal,
                self._session
            )
        else:
            self._clients[personal.device_sn].deye_personal = personal

        return self._clients[personal.device_sn]

    async def close(self):
        await self._session.close()
