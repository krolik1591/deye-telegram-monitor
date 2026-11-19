from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from settings.dotenv_config import dotenv_config

bot_ = Bot(token=dotenv_config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))