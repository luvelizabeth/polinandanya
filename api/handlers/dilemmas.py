import json
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import Dilemma
from api.database.db_queries import get_game_state

router = Router()

@router.message(Command("dilemma"))
@router.message(F.text == "🎭 Сыграть в дилеммы")
async def start_dilemma(message: Message, bot: Bot):
    async with async_session() as session:
        state = await get_game_state(session, "dilemma")
        if state.is_active:
            return await message.answer("Игра уже идет! Ждем ответа партнера.")
        
        result = await session.execute(select(Dilemma).where(Dilemma.is_used == False))
        dilemmas = result.scalars().all()
        if not dilemmas:
            return await message.answer("Все дилеммы закончились! 😢")
            
        dilemma = random.choice(dilemmas)
        dilemma.is_used = True
        
        state.is_active = True
        state.data = json.dumps({
            "question": dilemma.question,
            "options": {"1": dilemma.option1, "2": dilemma.option2},
            "answers": {}
        })
        await session.commit()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=dilemma.option1, callback_data="dil_1")],
        [InlineKeyboardButton(text=dilemma.option2, callback_data="dil_2")]
    ])
    msg_text = f"🤔 <b>Что бы ты выбрал?</b>\n\n{dilemma.question}"
    await bot.send_message(config.DANILA_ID, msg_text, reply_markup=kb)
    await bot.send_message(config.POLINA_ID, msg_text, reply_markup=kb)

@router.callback_query(F.data.startswith("dil_"))
async def handle_dilemma_answer(callback: CallbackQuery, bot: Bot):
    user_id = str(callback.from_user.id)
    choice_id = callback.data.split("_")[1]
    
    async with async_session() as session:
        state = await get_game_state(session, "dilemma")
        if not state.is_active:
            return await callback.answer("Эта игра завершена!", show_alert=True)
            
        data = json.loads(state.data)
        if user_id in data.get("answers", {}):
            return await callback.answer("Ты уже проголосовал!", show_alert=True)
            
        choice_text = data["options"][choice_id]
        if "answers" not in data:
            data["answers"] = {}
        data["answers"][user_id] = choice_text
        state.data = json.dumps(data)
        await session.commit()
        
    await callback.message.edit_text(f"Твой выбор: <b>{choice_text}</b>. Ждем партнера...")
    
    if len(data["answers"]) == 2:
        ans_danila = data["answers"].get(str(config.DANILA_ID))
        ans_polina = data["answers"].get(str(config.POLINA_ID))
        question = data["question"]
        
        async with async_session() as session:
            state = await get_game_state(session, "dilemma")
            state.is_active = False
            state.data = "{}"
            await session.commit()
            
        match_text = "Ваши ответы совпали! ❤️" if ans_danila == ans_polina else "Вы выбрали разное! ⚖️"
        await bot.send_message(config.CHAT_ID, f"🤔 <b>Итоги дилеммы</b>\n\nВопрос: {question}\n\nДаня: {ans_danila}\nПолина: {ans_polina}\n\n{match_text}")
