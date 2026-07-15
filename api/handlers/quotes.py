from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import Quote

router = Router()

class QuoteState(StatesGroup):
    waiting_for_forward = State()

@router.message(Command("add_quote"))
@router.message(F.text == "Добавить цитату")
async def start_add_quote(message: Message, state: FSMContext):
    await message.answer("Перешли мне сообщение для цитаты:")
    await state.set_state(QuoteState.waiting_for_forward)

@router.message(QuoteState.waiting_for_forward)
async def process_forwarded_quote(message: Message, state: FSMContext):
    if not message.forward_origin:
        return await message.answer("Это не пересланное сообщение!")
    text = message.text or message.caption
    if not text:
        return await message.answer("Нет текста.")
        
    author_name = "Неизвестный"
    if message.forward_origin.type == "user": author_name = message.forward_origin.sender_user.first_name
    elif message.forward_origin.type == "hidden_user": author_name = message.forward_origin.sender_user_name
        
    async with async_session() as session:
        session.add(Quote(text=text, author_name=author_name, added_by_id=message.from_user.id))
        await session.commit()
    await message.answer("✅ Цитата добавлена!")
    await state.clear()

@router.message(Command("quotes"))
@router.message(F.text == "Посмотреть цитаты")
async def view_quotes(message: Message):
    async with async_session() as session:
        res = await session.execute(select(Quote).order_by(Quote.date.desc()))
        quotes = res.scalars().all()
    if not quotes:
        return await message.answer("Цитатник пуст.")
    response = "📖 <b>Наш общий цитатник:</b>\n\n"
    for q in quotes:
        adder = "Даня" if q.added_by_id == config.DANILA_ID else "Полина"
        response += f"<i>«{q.text}»</i>\n— <b>{q.author_name}</b> ({adder}, {q.date.strftime('%d.%m.%Y')})\n\n"
    for i in range(0, len(response), 4000):
        await message.answer(response[i:i+4000])
