import json
import random
from fastapi import APIRouter, Request
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import AssociationWord, Reminder
from api.database.db_queries import get_game_state, update_balance
from api.utils.weather import get_weather
from datetime import datetime
from sqlalchemy import update

router = APIRouter(prefix="/api/cron")

@router.get("/reminders")
async def cron_send_reminders(request: Request):
    bot = request.app.state.bot
    now = datetime.utcnow()
    
    async with async_session() as session:
        # Get pending reminders that should have been sent by now
        res = await session.execute(
            select(Reminder).where(
                Reminder.send_at <= now,
                Reminder.is_sent == False
            )
        )
        reminders = res.scalars().all()
        
        if not reminders:
            return {"status": "no reminders to send"}
            
        sent_count = 0
        for r in reminders:
            sender_name = "Даня" if r.sender_id == config.DANILA_ID else "Полина"
            msg_text = (
                f"💌 <b>Заботливое напоминание от {sender_name}!</b>\n"
                f"─── ʚ ✨ ɞ ───\n\n"
                f"{r.text}"
            )
            try:
                await bot.send_message(r.receiver_id, msg_text)
                r.is_sent = True
                sent_count += 1
            except Exception as e:
                logging.error(f"Failed to send reminder {r.id}: {e}")
        
        await session.commit()
    
    return {"status": "ok", "sent": sent_count}

@router.get("/associations")
async def cron_associations(request: Request):
    bot = request.app.state.bot
    async with async_session() as session:
        state = await get_game_state(session, "association")
        if state.is_active: return {"status": "already active"}
        res = await session.execute(select(AssociationWord).where(AssociationWord.is_used == False))
        words = res.scalars().all()
        if not words: return {"status": "no words left"}
        word_obj = random.choice(words)
        word_obj.is_used = True
        state.is_active = True
        state.data = json.dumps({"word": word_obj.word, "answers": {}})
        await session.commit()
    msg = f"🧠 Игра «Телепатия» началась!\n\nВаше слово: <b>{word_obj.word}</b>\nНапишите первую ассоциацию!"
    await bot.send_message(config.DANILA_ID, msg)
    await bot.send_message(config.POLINA_ID, msg)
    return {"status": "ok"}

ROLES = [
    ("Шеф-повар, у которого сбежал лобстер", ["Как вы поняли, что он сбежал?", "Что сказали гостям?"]),
    ("Детектив, расследующий кражу носка", ["Кто главный подозреваемый?", "Какие улики найдены?"])
]

@router.get("/interview")
async def cron_interview(request: Request):
    bot = request.app.state.bot
    role, questions = random.choice(ROLES)
    q_text = "\n".join(f"- {q}" for q in questions)
    msg = f"🎬 <b>Актерское интервью!</b>\n\nТвоя роль: <b>{role}</b>\n\nВопросы:\n{q_text}\n\nЗаписывай голосовые (просто отправь ГС в чат)."
    await bot.send_message(config.DANILA_ID, msg)
    await bot.send_message(config.POLINA_ID, msg)
    return {"status": "ok"}

@router.get("/weather_morning")
async def cron_weather_morning(request: Request):
    bot = request.app.state.bot
    w = await get_weather(config.POLINA_CITY)
    if w:
        temp, desc = w["main"]["temp"], w["weather"][0]["description"]
        await bot.send_message(config.DANILA_ID, f"🌤 <b>Утро в {config.POLINA_CITY}:</b>\n{temp}°C, {desc}")
    return {"status": "ok"}

@router.get("/weather_check")
async def cron_weather_check(request: Request):
    bot = request.app.state.bot
    w = await get_weather(config.POLINA_CITY)
    if w:
        temp, desc = w["main"]["temp"], w["weather"][0]["description"].lower()
        if any(c in desc for c in ["дождь", "гроза", "шторм"]):
            await bot.send_message(config.DANILA_ID, f"⚠️ <b>В городе Полины плохая погода!</b>\n{temp}°C, {desc}.\nПрояви заботу! ❤️")
    return {"status": "ok"}
