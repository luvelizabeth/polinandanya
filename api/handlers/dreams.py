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

from api.handlers.menu import get_dreams_keyboard_nav

router = Router()

class DreamState(StatesGroup):
    recording = State()

def get_dreams_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Просмотреть сохраненные сны", callback_data="show_dreams")],
        [InlineKeyboardButton(text="✍️ Добавить новый сон", callback_data="add_dream")],
        [InlineKeyboardButton(text="❌ Свернуть", callback_data="close_menu")]
    ])

@router.message(F.text == "☁️ Наши сновидения")
async def dreams_menu(message: Message):
    await message.answer(
        "☁️ <b>ДНЕВНИК СНОВИДЕНИЙ</b>\n"
        "─── ʚ ☁️ ɞ ───\n\n"
        "Здесь хранятся наши самые странные, страшные и милые сны. Хочешь вспомнить прошлое или записать свежий сон?\n\n"
        "☁️ Выбери действие ниже",
        reply_markup=get_dreams_keyboard_nav()
    )

@router.message(F.text == "📖 Просмотреть сохраненные сны")
async def show_dreams_text(message: Message):
    await show_dreams(message)

@router.message(F.text == "✍️ Добавить новый сон")
async def add_dream_text(message: Message, state: FSMContext):
    await start_record_dream(message, state)

@router.callback_query(F.data == "close_menu")
async def close_menu_cb(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Свернуто", show_alert=False)

@router.callback_query(F.data == "add_dream")
@router.message(Command("record_dream"))
async def start_record_dream(message_or_cb, state: FSMContext):
    msg = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
    text = (
        "✍️ <b>Запись нового сна</b>\n\n"
        "Отправь мне текст или голосовое сообщение с рассказом о сне. "
        "Ты можешь отправить несколько сообщений подряд, а когда закончишь — нажми кнопку ниже."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сон полностью записан", callback_data="finish_dream")]])
    
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(text, reply_markup=kb)
        await message_or_cb.answer("Режим записи активирован")
    else:
        await msg.answer(text, reply_markup=kb)
        
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
        return await message.answer("⚠️ Пожалуйста, отправляй только текстовые или голосовые сообщения.")
    await state.update_data(dreams=dreams)
    await message.answer("✅ <i>Фрагмент добавлен! Можешь продолжить рассказ или нажать «Сон полностью записан».</i>")

@router.callback_query(F.data == "finish_dream", DreamState.recording)
async def finish_dream(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dreams = data.get("dreams", [])
    if not dreams:
        return await callback.answer("Ты еще ничего не записал!", show_alert=True)
        
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
        
    msg = "✨ <b>Сон успешно сохранен в дневник!</b>" + ("\n\n🎉 За первую запись за сегодня начислено <b>+5 ЛапКоинов</b>!" if is_first else "")
    await callback.message.edit_text(msg)
    await callback.answer("Успешно сохранено!", show_alert=False)
    await state.clear()

@router.callback_query(F.data == "show_dreams")
@router.message(Command("dreams"))
async def show_dreams(message_or_cb):
    msg = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
    async with async_session() as session:
        res = await session.execute(select(Dream).order_by(Dream.date.desc()))
        dreams = res.scalars().all()
    if not dreams:
        if isinstance(message_or_cb, CallbackQuery):
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌸 Назад", callback_data="dreams_menu")]])
            return await message_or_cb.message.edit_text(
                "☁️ <b>ДНЕВНИК СНОВ</b>\n"
                "─── ʚ ☁️ ɞ ───\n\n"
                "Дневник пока пуст... Самое время увидеть что-нибудь интересное! ✨", 
                reply_markup=kb
            )
        else:
            return await msg.answer("☁️ <b>Дневник пока пуст.</b>")
        
    grouped = {}
    for d in dreams:
        key = (d.date, d.user_id)
        if key not in grouped: grouped[key] = {"t": 0, "v": 0}
        if d.is_voice: grouped[key]["v"] += 1
        else: grouped[key]["t"] += 1
            
    buttons = []
    for (d_date, u_id), info in grouped.items():
        name = "Даня" if u_id == config.DANILA_ID else "Полина"
        t_count = f"{info['t']}📝" if info['t'] > 0 else ""
        v_count = f"{info['v']}🎙️" if info['v'] > 0 else ""
        counts = f"({t_count}{' ' if t_count and v_count else ''}{v_count})"
        btn_text = f"📅 {d_date.strftime('%d.%m.%y')} — {name} {counts}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"read_dream_{d_date.isoformat()}_{u_id}")])
    buttons.append([InlineKeyboardButton(text="🌸 В меню сновидений", callback_data="dreams_menu")])
    
    text = (
        "📖 <b>АРХИВ СНОВИДЕНИЙ</b>\n"
        "─── ʚ 📖 ɞ ───\n\n"
        "Выбери запись, чтобы прочитать или прослушать её детали. 👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(text, reply_markup=kb)
        await message_or_cb.answer("Загружено")
    else:
        await msg.answer(text, reply_markup=kb)

@router.callback_query(F.data == "dreams_menu")
async def back_to_dreams_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "☁️ <b>Дневник сновидений</b>\n\n"
        "Здесь хранятся все наши самые странные, страшные и милые сны. "
        "Хочешь вспомнить, что нам снилось, или записать свежий сон?",
        reply_markup=get_dreams_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("read_dream_"))
async def read_dream_cb(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    d_date = date.fromisoformat(parts[2])
    u_id = int(parts[3])
    async with async_session() as session:
        res = await session.execute(select(Dream).where(Dream.user_id == u_id, Dream.date == d_date))
        dreams = res.scalars().all()
    name = "Даня" if u_id == config.DANILA_ID else "Полина"
    
    text = (
        f"💤 <b>СОН: {name}</b>\n"
        f"📅 <b>Дата:</b> {d_date.strftime('%d.%m.%Y')}\n"
        f"─── ʚ 💤 ɞ ───\n\n"
    )
    voices = []
    for d in dreams:
        if d.is_voice:
            voices.append(d.content)
        else:
            text += f"📝 <i>«{d.content}»</i>\n\n"
    
    if voices:
        text += f"🎙 <b>Голосовые фрагменты:</b> {len(voices)} шт.\n<i>(Будут отправлены ниже)</i>"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌸 К списку снов", callback_data="show_dreams")]])
    await callback.message.edit_text(text, reply_markup=kb)
    
    for v in voices:
        await bot.send_voice(callback.message.chat.id, v)
        
    await callback.answer("Сон загружен!")
