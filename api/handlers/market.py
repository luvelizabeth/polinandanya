from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import Lot
from api.database.db_queries import get_or_create_user

router = Router()

class CreateLotState(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()

@router.message(Command("create_lot"))
@router.message(F.text == "Создать лот")
async def create_lot_start(message: Message, state: FSMContext):
    await message.answer("Отправь мне медиафайл (фото, видео, ГС, кружок) или текст для лота:")
    await state.set_state(CreateLotState.waiting_for_media)

@router.message(CreateLotState.waiting_for_media)
async def process_media(message: Message, state: FSMContext):
    media_file_id = None
    media_type = "text"
    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.voice:
        media_file_id = message.voice.file_id
        media_type = "voice"
    elif message.video_note:
        media_file_id = message.video_note.file_id
        media_type = "video_note"
    elif message.text:
        media_file_id = message.text
        media_type = "text"
    else:
        await message.answer("Неподдерживаемый тип сообщения.")
        return
    await state.update_data(media_file_id=media_file_id, media_type=media_type)
    await message.answer("Отлично! Теперь введи заголовок лота:")
    await state.set_state(CreateLotState.waiting_for_title)

@router.message(CreateLotState.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введи описание лота:")
    await state.set_state(CreateLotState.waiting_for_description)

@router.message(CreateLotState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введи цену лота (в ЛапКоинах, только число):")
    await state.set_state(CreateLotState.waiting_for_price)

@router.message(CreateLotState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи только число.")
    price = int(message.text)
    data = await state.get_data()
    async with async_session() as session:
        lot = Lot(owner_id=message.from_user.id, title=data['title'], description=data['description'],
                  price=price, media_file_id=data['media_file_id'], media_type=data['media_type'])
        session.add(lot)
        await session.commit()
    await message.answer("✅ Лот успешно создан и добавлен в магазин!")
    await state.clear()

@router.message(Command("shop"))
@router.message(F.text == "Магазин")
async def shop_handler(message: Message):
    partner_id = config.POLINA_ID if message.from_user.id == config.DANILA_ID else config.DANILA_ID
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == partner_id, Lot.is_active == True))
        lots = result.scalars().all()
    if not lots:
        return await message.answer("Магазин партнера пока пуст.")
    for lot in lots:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Купить за {lot.price} 🪙", callback_data=f"buy_lot_{lot.id}")]])
        await message.answer(f"📦 <b>{lot.title}</b>\n\n{lot.description}\n\nЦена: {lot.price} 🪙", reply_markup=kb)

@router.callback_query(F.data.startswith("buy_lot_"))
async def buy_lot_callback(callback: CallbackQuery, bot: Bot):
    lot_id = int(callback.data.split("_")[2])
    buyer_id = callback.from_user.id
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        if not lot or not lot.is_active:
            return await callback.answer("Лот недоступен.", show_alert=True)
        buyer = await get_or_create_user(session, buyer_id)
        if buyer.balance < lot.price:
            return await callback.answer("Недостаточно ЛапКоинов!", show_alert=True)
        buyer.balance -= lot.price
        seller_income = lot.price // 2
        seller = await get_or_create_user(session, lot.owner_id)
        seller.balance += seller_income
        lot.is_active = False
        await session.commit()
    
    await callback.message.edit_text(f"✅ Лот «{lot.title}» успешно куплен!")
    if lot.media_type == "text":
        await bot.send_message(buyer_id, f"Содержимое лота «{lot.title}»:\n{lot.media_file_id}")
    elif lot.media_type == "photo":
        await bot.send_photo(buyer_id, lot.media_file_id, caption=f"Лот «{lot.title}»")
    elif lot.media_type == "video":
        await bot.send_video(buyer_id, lot.media_file_id, caption=f"Лот «{lot.title}»")
    elif lot.media_type == "voice":
        await bot.send_voice(buyer_id, lot.media_file_id, caption=f"Лот «{lot.title}»")
    elif lot.media_type == "video_note":
        await bot.send_video_note(buyer_id, lot.media_file_id)
    await bot.send_message(lot.owner_id, f"Твой лот «{lot.title}» выкуплен за {lot.price} коинов! Получено {seller_income} 🪙.")
    await callback.answer()
