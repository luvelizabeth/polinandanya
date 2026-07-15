import random
from datetime import date
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from api.database.connection import async_session
from api.database.db_queries import get_or_create_user

router = Router()

@router.message(Command("bonus"))
@router.message(F.text == "Ежедневный бонус")
async def daily_bonus_handler(message: Message):
    amount = random.randint(5, 15)
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        today = date.today()
        if user.last_bonus_date == today:
            await message.answer(f"Сегодня ты уже получал бонус! Заходи завтра.\nТвой баланс: {user.balance} 🪙")
        else:
            user.balance += amount
            user.last_bonus_date = today
            await session.commit()
            await message.answer(f"🎉 Ты получил ежедневный бонус: {amount} ЛапКоинов!\nТвой баланс: {user.balance} 🪙")

@router.message(Command("balance"))
@router.message(F.text == "Баланс")
async def balance_handler(message: Message):
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await message.answer(f"Твой баланс: {user.balance} ЛапКоинов 🪙")
