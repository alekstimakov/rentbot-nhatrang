from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer("Welcome! Use this bot to rent a bike.")
