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
@router.message(F.text == "🎁 Создать лот")
async def create_lot_start(message: Message, state: FSMContext):
    await message.answer("🎁 <b>Создание нового лота</b>\n\nОтправь мне медиафайл (фото, видео, ГС, кружок) или текст, который будет содержимым лота:")
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
@router.message(F.text == "🛍️ Магазин чудес")
async def shop_main_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Посмотреть лоты партнера", callback_data="shop_partner_lots")],
        [InlineKeyboardButton(text="📦 Мои лоты", callback_data="shop_my_lots")],
        [InlineKeyboardButton(text="❌ Свернуть", callback_data="shop_close")]
    ])
    await message.answer(
        "🛍️ <b>Магазин чудес</b>\n\n"
        "Здесь ты можешь потратить свои ЛапКоины на лоты партнера или управлять своими собственными лотами.",
        reply_markup=kb
    )

@router.callback_query(F.data == "shop_main")
async def shop_main_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Посмотреть лоты партнера", callback_data="shop_partner_lots")],
        [InlineKeyboardButton(text="📦 Мои лоты", callback_data="shop_my_lots")],
        [InlineKeyboardButton(text="❌ Свернуть", callback_data="shop_close")]
    ])
    await callback.message.edit_text(
        "🛍️ <b>Магазин чудес</b>\n\n"
        "Здесь ты можешь потратить свои ЛапКоины на лоты партнера или управлять своими собственными лотами.",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data == "shop_close")
async def shop_close_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Свернуто", show_alert=False)

@router.callback_query(F.data == "shop_partner_lots")
async def shop_partner_lots(callback: CallbackQuery):
    partner_id = config.POLINA_ID if callback.from_user.id == config.DANILA_ID else config.DANILA_ID
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == partner_id, Lot.is_active == True))
        lots = result.scalars().all()
        
    if not lots:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")]])
        return await callback.message.edit_text("🛍️ <b>Магазин партнера пока пуст.</b>\nЖдем новых лотов!", reply_markup=kb)
        
    buttons = []
    for lot in lots:
        buttons.append([InlineKeyboardButton(text=f"📦 {lot.title} ({lot.price} 🪙)", callback_data=f"shop_view_{lot.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")])
    
    await callback.message.edit_text(
        "🛍️ <b>Лоты партнера:</b>\n<i>Выбери лот, чтобы узнать подробности и купить.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data == "shop_my_lots")
async def shop_my_lots(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == callback.from_user.id))
        lots = result.scalars().all()
        
    if not lots:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")]])
        return await callback.message.edit_text("📦 <b>У тебя пока нет созданных лотов.</b>", reply_markup=kb)
        
    buttons = []
    for lot in lots:
        status = "✅" if lot.is_active else "❌ (продан)"
        buttons.append([InlineKeyboardButton(text=f"{status} {lot.title}", callback_data=f"shop_view_my_{lot.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_main")])
    
    await callback.message.edit_text(
        "📦 <b>Твои лоты:</b>\n<i>Нажми на лот для просмотра.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("shop_view_"))
async def shop_view_lot(callback: CallbackQuery):
    is_mine = callback.data.startswith("shop_view_my_")
    lot_id = int(callback.data.replace("shop_view_my_", "").replace("shop_view_", ""))
    
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        
    if not lot:
        return await callback.answer("Лот не найден!", show_alert=True)
        
    text = f"📦 <b>{lot.title}</b>\n\n{lot.description}\n\nЦена: <b>{lot.price} 🪙</b>\n"
    text += f"Статус: {'✅ Активен' if lot.is_active else '❌ Продан'}"
    
    buttons = []
    if is_mine:
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_my_lots")])
    else:
        if lot.is_active:
            buttons.append([InlineKeyboardButton(text=f"💳 Купить за {lot.price} 🪙", callback_data=f"buy_lot_{lot.id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_partner_lots")])
        
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("buy_lot_"))
async def buy_lot_callback(callback: CallbackQuery, bot: Bot):
    lot_id = int(callback.data.split("_")[2])
    buyer_id = callback.from_user.id
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        if not lot or not lot.is_active:
            return await callback.answer("Лот недоступен или уже продан.", show_alert=True)
        buyer = await get_or_create_user(session, buyer_id)
        if buyer.balance < lot.price:
            return await callback.answer("Недостаточно ЛапКоинов для покупки!", show_alert=True)
        
        buyer.balance -= lot.price
        seller_income = lot.price // 2
        seller = await get_or_create_user(session, lot.owner_id)
        seller.balance += seller_income
        lot.is_active = False
        await session.commit()
    
    # Update current message
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к лотам", callback_data="shop_partner_lots")]])
    await callback.message.edit_text(f"✅ <b>Лот «{lot.title}» успешно куплен!</b>\n\nЯ отправил содержимое лота отдельным сообщением.", reply_markup=kb)
    
    if lot.media_type == "text":
        await bot.send_message(buyer_id, f"📦 <b>Содержимое лота «{lot.title}»:</b>\n\n{lot.media_file_id}")
    elif lot.media_type == "photo":
        await bot.send_photo(buyer_id, lot.media_file_id, caption=f"📦 Лот «{lot.title}»")
    elif lot.media_type == "video":
        await bot.send_video(buyer_id, lot.media_file_id, caption=f"📦 Лот «{lot.title}»")
    elif lot.media_type == "voice":
        await bot.send_voice(buyer_id, lot.media_file_id, caption=f"📦 Лот «{lot.title}»")
    elif lot.media_type == "video_note":
        await bot.send_video_note(buyer_id, lot.media_file_id)
        await bot.send_message(buyer_id, f"📦 Лот «{lot.title}»")
        
    await bot.send_message(lot.owner_id, f"🎉 <b>Твой лот «{lot.title}» выкуплен!</b>\nПолучено {seller_income} 🪙 (комиссия 50%).")
    await callback.answer("Лот куплен!", show_alert=False)
