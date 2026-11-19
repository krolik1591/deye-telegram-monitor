import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, types

from bot_ import bot_ as bot
from db.mongodb import create_db_indexes
from handlers import routers
from middlewares.skip_guests import SkipGuestsMiddleware
from services.bootstrap import ensure_first_personal
from services.master_service import create_master_service
from settings.electric_members import electric_members
from utils.check_internet_connection import check_internet_connection


async def main() -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Starting bot..")

    if not await check_internet_connection():
        logging.info("Internet connection is down.")
        exit(1)

    master_service = create_master_service()

    # DB setup must happen before we look at personals
    await create_db_indexes()
    await ensure_first_personal()
    await electric_members.update()

    background_tasks = [
        asyncio.create_task(master_service.new_yasno.start()),
        asyncio.create_task(master_service.plugs.start()),
    ]

    dp = Dispatcher(master_service=master_service)
    dp.callback_query.middleware(SkipGuestsMiddleware())
    dp.message.middleware(SkipGuestsMiddleware())
    for router in routers:
        dp.include_router(router)

    await set_bot_commands(bot)

    await master_service.run()

    try:
        await dp.start_polling(bot)
    finally:
        for t in background_tasks:
            t.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)
        await master_service.deye_client_manager.close()


async def set_bot_commands(bot: Bot):
    # Reply-kb buttons cover everything in-app. Only expose /start in the
    # hamburger menu so a user can always re-pin the welcome + reply-kb.
    await bot.set_my_commands(
        commands=[types.BotCommand(command="start", description="🚀 Запустити бота")],
        scope=types.BotCommandScopeAllPrivateChats(),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
