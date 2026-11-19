import logging
from asyncio import sleep

from aiogram import exceptions

from bot_ import bot_
from db import mongodb
from settings.dotenv_config import dotenv_config


class MessageService:
    def __init__(self):
        self.bot = bot_
        # If the Deye bootstrap env is present (first-boot seed), route dev
        # notifications to those user_ids; otherwise fall back to const.DEV so
        # the bot can boot on an already-seeded deployment without the .env
        # bootstrap block.
        self.dev_ids = dotenv_config.deye_basic.user_ids

    async def to_devs(self, message: str):
        await self.send_msgs(self.dev_ids, message)

    async def to_channel(self, channel_id: int, message: str):
        try:
            await self.bot.send_message(chat_id=channel_id, text=message)
        except Exception as e:
            logging.error(f"Can't send message to channel {channel_id}: {e}")

    async def send_msgs(self, user_ids: list[int], message: str):
        for user_id in user_ids:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                await sleep(1)
            except Exception as e:
                logging.error(f"Can't send message to {user_id}: {e}")

    async def send_new_schedule(self, channel_id: int, message: str):
        try:
            msg = await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                disable_notification=True,
            )
            await self.bot.pin_chat_message(
                chat_id=channel_id,
                message_id=msg.message_id,
                disable_notification=True,
            )
            await mongodb.update_schedule_msg_id(channel_id, msg.message_id)

        except Exception as e:
            err = f"Can't send schedule to channel {channel_id}: {e}"
            logging.error(err)
            await self.to_devs(err)

    async def update_schedule(self, channel_id: int, message: str):
        try:
            msg_id = await mongodb.get_schedule_msg_id(channel_id)
            if msg_id is None:
                # no pinned message yet for this channel — fall back to a fresh post+pin
                await self.send_new_schedule(channel_id, message)
                return
            await self.bot.edit_message_text(
                text=message,
                chat_id=channel_id,
                message_id=msg_id,
            )

        except exceptions.TelegramBadRequest as e:
            logging.info(f"Can't edit channel {channel_id} msg: text the same. {e}")
        except Exception as e:
            err = f"Can't update schedule in channel {channel_id}: {e}"
            logging.error(err)
            await self.to_devs(err)


def create_message_service() -> MessageService:
    return MessageService()
