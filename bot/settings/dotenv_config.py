import logging
import os
from typing import Optional

from dotenv import load_dotenv

from settings.helpers import _looks_hashed, _sha256, _persist_env
from types_.mixin_types import BasicDeyePersonal

load_dotenv()


class DotEnvConfig:
    def __init__(self):
        self.stage = os.getenv("STAGE")

        self.bot_token = self.get_bot_token()
        self.mongo_connection_string = os.getenv("MONGO_CONNECTION_STRING")

        self.tapo_username = os.getenv("TAPO_USERNAME")
        self.tapo_password = os.getenv("TAPO_PASSWORD")

        # Optional bootstrap payload for the FIRST DeyePersonal. Only consumed
        # by services.bootstrap.ensure_first_personal() when the collection
        # is empty. If any required var is missing, this is None and the
        # admin can seed manually via tests/add_deye_personal.py.
        self.deye_basic = self._try_load_deye_basic()

    def get_bot_token(self):
        if self.stage == "dev":
            return os.getenv("DEV_BOT_TOKEN")
        return os.getenv("PROD_BOT_TOKEN")

    # ------- deye bootstrap -------

    def _try_load_deye_basic(self) -> Optional[BasicDeyePersonal]:
        required = {
            "USER_ID": os.getenv("USER_ID"),
            "DEVICE_SN": os.getenv("DEVICE_SN"),
            "APP_ID": os.getenv("APP_ID"),
            "APP_SECRET": os.getenv("APP_SECRET"),
            "EMAIL": os.getenv("EMAIL"),
            "PASSWORD": os.getenv("PASSWORD"),
            "BATTERY_CAPACITY_KWH": os.getenv("BATTERY_CAPACITY_KWH"),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            logging.info(
                f"DotEnvConfig: Deye bootstrap unavailable, missing env: {', '.join(missing)}"
            )
            return None

        try:
            password = self._ensure_hashed_password(required["PASSWORD"])
            return BasicDeyePersonal(
                user_ids=[int(required["USER_ID"])],
                app_id=int(required["APP_ID"]),
                app_secret=required["APP_SECRET"],
                email=required["EMAIL"],
                password=password,
                device_sn=int(required["DEVICE_SN"]),
                battery_capacity_kwh=int(required["BATTERY_CAPACITY_KWH"]),
            )
        except (TypeError, ValueError) as e:
            logging.warning(f"DotEnvConfig: can't parse Deye bootstrap env: {e}")
            return None

    @staticmethod
    def _ensure_hashed_password(raw: str) -> str:
        if _looks_hashed(raw):
            return raw
        hashed = _sha256(raw)
        _persist_env("PASSWORD", hashed)
        logging.info("DotEnvConfig: PASSWORD was plaintext — hashed and persisted to .env")
        return hashed


def create_dotenv_config():
    return DotEnvConfig()


dotenv_config = create_dotenv_config()
