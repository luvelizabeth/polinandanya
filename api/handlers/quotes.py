from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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

def get_quotes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Просмотреть цитаты", callback_data="show_quotes")],
        [InlineKeyboardButton(text="✍️ Добавить цитату", callback_data="add_quote")],
        [InlineKeyboardButton(text="❌ Свернуть", callback_data="close_menu")]
    ])

@router.message(F.text == "💬 Копилка цитат")
async def quotes_menu(message: Message):
    await message.answer(
        "💬 <b>Наша копилка цитат</b>\n\n"
        "Сборник наших локальных мемов, смешных фраз и важных слов. "
        "Что будем делать?",
        reply_markup=get_quotes_keyboard()
    )

@router.callback_query(F.data == "close_menu")
async def close_menu_cb(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Свернуто", show_alert=False)

@router.callback_query(F.data == "add_quote")
@router.message(Command("add_quote"))
async def start_add_quote(message_or_cb, state: FSMContext):
    msg = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
    text = (
        "✍️ <b>Добавление новой цитаты</b>\n\n"
        "Просто перешли мне любое смешное или важное сообщение (с текстом), и я сохраню его в нашу копилку!"
    )
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(text)
        await message_or_cb.answer("Жду пересланное сообщение", show_alert=False)
    else:
        await msg.answer(text)
    await state.set_state(QuoteState.waiting_for_forward)

@router.message(QuoteState.waiting_for_forward)
async def process_forwarded_quote(message: Message, state: FSMContext):
    if not message.forward_origin:
        return await message.answer("⚠️ Пожалуйста, <b>перешли</b> сообщение, а не просто отправь текст.")
    text = message.text or message.caption
    if not text:
        return await message.answer("⚠️ В пересланном сообщении нет текста.")
        
    author_name = "Неизвестный"
    if message.forward_origin.type == "user": author_name = message.forward_origin.sender_user.first_name
    elif message.forward_origin.type == "hidden_user": author_name = message.forward_origin.sender_user_name
        
    async with async_session() as session:
        session.add(Quote(text=text, author_name=author_name, added_by_id=message.from_user.id))
        await session.commit()
    await message.answer(f"✅ <b>Отлично!</b>\nЦитата от <i>{author_name}</i> успешно сохранена в копилку!")
    await state.clear()

@router.callback_query(F.data.startswith("show_quotes"))
@router.message(Command("quotes"))
async def view_quotes(message_or_cb):
    page = 0
    if isinstance(message_or_cb, CallbackQuery) and "page_" in message_or_cb.data:
        page = int(message_or_cb.data.split("_")[-1])
        
    msg = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
    async with async_session() as session:
        res = await session.execute(select(Quote).order_by(Quote.date.desc()))
        quotes = res.scalars().all()
        
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="quotes_menu")]])
        
    if not quotes:
        if isinstance(message_or_cb, CallbackQuery):
            return await message_or_cb.message.edit_text("📜 <b>Цитатник пока пуст.</b>", reply_markup=kb_back)
        else:
            return await msg.answer("📜 <b>Цитатник пока пуст.</b>")
            
    quotes_per_page = 5
    total_pages = (len(quotes) + quotes_per_page - 1) // quotes_per_page
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    
    start_idx = page * quotes_per_page
    end_idx = start_idx + quotes_per_page
    page_quotes = quotes[start_idx:end_idx]
    
    response = f"📜 <b>Наш общий цитатник (Страница {page+1}/{total_pages}):</b>\n\n"
    for q in page_quotes:
        adder = "Даня" if q.added_by_id == config.DANILA_ID else "Полина"
        response += f"<i>«{q.text}»</i>\n— <b>{q.author_name}</b> <i>(добавил(а) {adder}, {q.date.strftime('%d.%m.%Y')})</i>\n\n"
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"show_quotes_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"show_quotes_page_{page+1}"))
        
    buttons = []
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text="⬅️ В меню цитат", callback_data="quotes_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(response, reply_markup=kb)
        await message_or_cb.answer()
    else:
        await msg.answer(response, reply_markup=kb)

@router.callback_query(F.data == "quotes_menu")
async def back_to_quotes_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💬 <b>Наша копилка цитат</b>\n\n"
        "Сборник наших локальных мемов, смешных фраз и важных слов. "
        "Что будем делать?",
        reply_markup=get_quotes_keyboard()
    )
    await callback.answer()
