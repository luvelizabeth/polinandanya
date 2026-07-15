import random
from datetime import date
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from api.database.connection import async_session
from api.database.db_queries import get_or_create_user

router = Router()

@router.message(Command("balance"))
@router.message(F.text == "💰 Мой баланс")
async def balance_handler(message: Message):
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await message.answer(
            f"💼 <b>Твой кошелек</b>\n\n"
            f"Внутри приятно звенят ЛапКоины.\n"
            f"💰 Баланс: <b>{user.balance} 🪙</b>"
        )
