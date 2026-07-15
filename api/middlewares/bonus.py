import random
from datetime import date
from aiogram import BaseMiddleware
from aiogram.types import Update
from api.database.connection import async_session
from api.database.db_queries import get_or_create_user

class AutoBonusMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        user = data.get("event_from_user")
        # We only want to trigger this for messages or callbacks, not all updates.
        # But data['event_from_user'] is usually present.
        if user and event.message:
            async with async_session() as session:
                db_user = await get_or_create_user(session, user.id)
                today = date.today()
                if db_user.last_bonus_date != today:
                    amount = random.randint(5, 15)
                    db_user.balance += amount
                    db_user.last_bonus_date = today
                    await session.commit()
                    
                    # Notify user
                    bot = data.get("bot")
                    if bot:
                        await bot.send_message(
                            chat_id=user.id,
                            text=(
                                f"☀️ <b>С возвращением!</b>\n\n"
                                f"Ты зашел сюда впервые за сегодня, и я начислил тебе ежедневный бонус!\n\n"
                                f"🎉 Получено: <b>{amount} ЛапКоинов</b>\n"
                                f"💰 Твой текущий баланс: <b>{db_user.balance} 🪙</b>"
                            )
                        )
        return await handler(event, data)
