from datetime import date
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import Dream
from api.database.db_queries import update_balance

router = Router()

class DreamState(StatesGroup):
    recording = State()

@router.message(Command("record_dream"))
@router.message(F.text == "Записать сон")
async def start_record_dream(message: Message, state: FSMContext):
    await message.answer("Отправь мне текст или голосовое (можно несколько), затем нажми кнопку.",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сон записан", callback_data="finish_dream")]]))
    await state.set_state(DreamState.recording)
    await state.update_data(dreams=[])

@router.message(DreamState.recording)
async def process_dream_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    dreams = data.get("dreams", [])
    if message.voice:
        dreams.append({"type": "voice", "content": message.voice.file_id})
    elif message.text:
        dreams.append({"type": "text", "content": message.text})
    else:
        return await message.answer("Только текст или голосовые.")
    await state.update_data(dreams=dreams)
    await message.answer("Добавлено! Пиши еще или жми 'Сон записан'.")

@router.callback_query(F.data == "finish_dream", DreamState.recording)
async def finish_dream(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dreams = data.get("dreams", [])
    if not dreams:
        return await callback.answer("Ничего не записано!", show_alert=True)
        
    user_id = callback.from_user.id
    today = date.today()
    
    async with async_session() as session:
        res = await session.execute(select(Dream).where(Dream.user_id == user_id, Dream.date == today))
        is_first = len(res.scalars().all()) == 0
        
        for d in dreams:
            session.add(Dream(user_id=user_id, date=today, content=d["content"], is_voice=(d["type"]=="voice")))
            
        if is_first:
            await update_balance(session, user_id, 5)
        await session.commit()
        
    msg = "✅ Сон сохранен!" + ("\n🎉 +5 ЛапКоинов за первый сон!" if is_first else "")
    await callback.message.edit_text(msg)
    await state.clear()

@router.message(Command("dreams"))
@router.message(F.text == "Наши сны")
async def show_dreams(message: Message):
    async with async_session() as session:
        res = await session.execute(select(Dream).order_by(Dream.date.desc()))
        dreams = res.scalars().all()
    if not dreams:
        return await message.answer("Дневник пуст.")
        
    grouped = {}
    for d in dreams:
        key = (d.date, d.user_id)
        if key not in grouped: grouped[key] = {"t": 0, "v": 0}
        if d.is_voice: grouped[key]["v"] += 1
        else: grouped[key]["t"] += 1
            
    for (d_date, u_id), info in grouped.items():
        name = "Даня" if u_id == config.DANILA_ID else "Полина"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Читать/Слушать", callback_data=f"read_dream_{d_date.isoformat()}_{u_id}")]])
        await message.answer(f"📅 {d_date.strftime('%d.%m.%Y')} — Сон {name} ({info['t']} текста, {info['v']} ГС)", reply_markup=kb)

@router.callback_query(F.data.startswith("read_dream_"))
async def read_dream_cb(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    d_date = date.fromisoformat(parts[2])
    u_id = int(parts[3])
    async with async_session() as session:
        res = await session.execute(select(Dream).where(Dream.user_id == u_id, Dream.date == d_date))
        dreams = res.scalars().all()
    name = "Даня" if u_id == config.DANILA_ID else "Полина"
    await callback.message.answer(f"💤 <b>Сон {name} от {parts[2]}:</b>")
    for d in dreams:
        if d.is_voice: await bot.send_voice(callback.message.chat.id, d.content)
        else: await callback.message.answer(d.content)
    await callback.answer()
