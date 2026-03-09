from aiogram import Dispatcher

from app.bot.handlers.start import router as start_router


def build_dispatcher(_: str) -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start_router)
    return dp
