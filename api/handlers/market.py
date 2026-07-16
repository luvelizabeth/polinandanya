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

from api.handlers.menu import get_shop_keyboard

router = Router()

class CreateLotState(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()

@router.message(Command("create_lot"))
@router.message(F.text == "🎀 Создать лот")
async def create_lot_start(message: Message, state: FSMContext):
    await message.answer(
        "🎀 <b>НОВЫЙ ЛОТ</b>\n"
        "─── ʚ 🎀 ɞ ───\n\n"
        "Давай создадим что-то особенное! Пришли мне медиафайл (фото, видео, ГС, кружок) или текст, который станет содержимым твоего лота.\n\n"
        "🎀 Твой партнер будет в восторге!"
    )
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
        await message.answer("🍭 <i>Ой, такой формат я пока не понимаю. Попробуй отправить что-то другое!</i>")
        return
    await state.update_data(media_file_id=media_file_id, media_type=media_type)
    await message.answer(
        "🍰 <b>ЗАГОЛОВОК</b>\n"
        "─── ʚ 🍰 ɞ ───\n\n"
        "Придумай милое название для своего лота. Оно будет отображаться в вашем магазине чудес!"
    )
    await state.set_state(CreateLotState.waiting_for_title)

@router.message(CreateLotState.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer(
        "🍰 <b>ОПИСАНИЕ</b>\n"
        "─── ʚ 🍰 ɞ ───\n\n"
        "Расскажи немного подробнее, что это за чудо? Твое описание поможет партнеру сделать выбор"
    )
    await state.set_state(CreateLotState.waiting_for_description)

@router.message(CreateLotState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "🍰 <b>СТОИМОСТЬ</b>\n"
        "─── ʚ 🍰 ɞ ───\n\n"
        "Сколько Лапкоинов должен стоить этот лот?\n"
        "Введи только число, Лапонька!"
    )
    await state.set_state(CreateLotState.waiting_for_price)

@router.message(CreateLotState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("🐾 <i>Котик, введи, пожалуйста, только число!</i>")
    price = int(message.text)
    data = await state.get_data()
    async with async_session() as session:
        lot = Lot(owner_id=message.from_user.id, title=data['title'], description=data['description'],
                  price=price, media_file_id=data['media_file_id'], media_type=data['media_type'])
        session.add(lot)
        await session.commit()
    await message.answer(
        "🎀 <b>УСПЕХ!</b>\n"
        "─── ʚ 🎀 ɞ ───\n\n"
        "Твой лот успешно создан и уже красуется на витрине! Теперь партнер может его выкупить."
    )
    await state.clear()

@router.message(Command("shop"))
@router.message(F.text == "🍭 Магазин чудес")
async def shop_main_menu(message: Message):
    await message.answer(
        "🍭 <b>МАГАЗИН ЧУДЕС</b>\n"
        "─── ʚ 🍭 ɞ ───\n\n"
        "Здесь ты можешь обменять накопленные Лапкоины на уникальные лоты от своего партнера!\n\n"
        "🍭 <b>Выбери действие</b>",
        reply_markup=get_shop_keyboard()
    )

@router.message(F.text == "🎁 Посмотреть лоты партнера")
async def shop_partner_lots_text(message: Message):
    partner_id = config.POLINA_ID if message.from_user.id == config.DANILA_ID else config.DANILA_ID
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == partner_id, Lot.is_active == True))
        lots = result.scalars().all()
        
    if not lots:
        return await message.answer(
            "🍭 <b>МАГАЗИН ПАРТНЕРА</b>\n"
            "─── ʚ 🍭 ɞ ───\n\n"
            "Пока что здесь пусто.. Но!\n"
            "Мы ждем новых поступлений!"
        )
        
    buttons = []
    type_icons = {"photo": "🖼️", "video": "🎬", "voice": "🎙️", "video_note": "⭕", "text": "📝"}
    
    for lot in lots:
        icon = type_icons.get(lot.media_type, "🍭")
        buttons.append([InlineKeyboardButton(text=f"{icon} {lot.title} — {lot.price} 🐾", callback_data=f"shop_view_{lot.id}")])
    
    await message.answer(
        "🍭 <b>ЛОТЫ ПАРТНЕРА</b>\n"
        "─── ʚ 🛍️ ɞ ───\n\n"
        "Нажми на интересующий лот, чтобы узнать подробности и совершить покупку. 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.message(F.text == "🍭 Мои лоты")
async def shop_my_lots_text(message: Message):
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == message.from_user.id))
        lots = result.scalars().all()
        
    if not lots:
        return await message.answer(
            "💖 <b>ТВОИ ЛОТЫ</b>\n"
            "─── ʚ 💖 ɞ ───\n\n"
            "У тебя пока нет созданных лотов.\n"
            "Время что-нибудь придумать! 💖"
        )
        
    buttons = []
    type_icons = {"photo": "🖼️", "video": "🎬", "voice": "🎙️", "video_note": "⭕", "text": "📝"}
    
    for lot in lots:
        status = "🍭" if lot.is_active else "❌"
        icon = type_icons.get(lot.media_type, "🎀")
        buttons.append([InlineKeyboardButton(text=f"{status} {icon} {lot.title}", callback_data=f"shop_view_my_{lot.id}")])
    
    await message.answer(
        "💖 <b>ТВОИ ЛОТЫ</b>\n"
        "─── ʚ 💖 ɞ ───\n\n"
        "Твои активные и проданные предложения. Нажми для управления. 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "shop_main")
async def shop_main_callback(callback: CallbackQuery):
    await shop_main_menu(callback.message)
    await callback.answer()

@router.callback_query(F.data == "shop_close")
async def shop_close_callback(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Свернуто", show_alert=False)

@router.callback_query(F.data == "shop_partner_lots")
async def shop_partner_lots(callback: CallbackQuery):
    await shop_partner_lots_text(callback.message)
    await callback.answer()

@router.callback_query(F.data == "shop_my_lots")
async def shop_my_lots(callback: CallbackQuery):
    await shop_my_lots_text(callback.message)
    await callback.answer()

@router.callback_query(F.data.startswith("shop_view_"))
async def shop_view_lot(callback: CallbackQuery):
    is_mine = callback.data.startswith("shop_view_my_")
    lot_id = int(callback.data.replace("shop_view_my_", "").replace("shop_view_", ""))
    
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        
    if not lot:
        return await callback.answer("🍭 Лот не найден!", show_alert=True)
        
    type_names = {"photo": "Фотография 🖼️", "video": "Видео 🎬", "voice": "Голосовое сообщение 🎙️", "video_note": "Видеосообщение ⭕", "text": "Текст 📝"}
    m_type = type_names.get(lot.media_type, "Контент 🍭")
    
    text = (
        f"✨ <b>ИНФОРМАЦИЯ О ЛОТЕ</b>\n"
        f"─── ʚ 🍭 ɞ ───\n\n"
        f"🏷 <b>Название:</b> {lot.title}\n"
        f"📝 <b>Описание:</b> {lot.description}\n"
        f"📂 <b>Тип контента:</b> {m_type}\n"
        f"🐾 <b>Стоимость:</b> {lot.price} Лапкоинов\n\n"
        f"📊 <b>Статус:</b> {'🍭 Доступен' if lot.is_active else '❌ Продан'}"
    )
    
    buttons = []
    if is_mine:
        if lot.is_active:
            buttons.append([InlineKeyboardButton(text="🗑 Удалить лот", callback_data=f"confirm_delete_{lot.id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ К списку моих лотов", callback_data="shop_my_lots")])
    else:
        if lot.is_active:
            buttons.append([InlineKeyboardButton(text=f"💳 Купить за {lot.price} 🐾", callback_data=f"buy_lot_{lot.id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ К витрине партнера", callback_data="shop_partner_lots")])
        
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_lot(callback: CallbackQuery):
    lot_id = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_lot_{lot_id}")],
        [InlineKeyboardButton(text="❌ Нет, оставить", callback_data=f"shop_view_my_{lot_id}")]
    ])
    await callback.message.edit_text(
        "⚠️ <b>ПОДТВЕРЖДЕНИЕ</b>\n"
        "─── ʚ 🗑 ɞ ───\n\n"
        "Ты действительно хочешь удалить этот лот? Это действие нельзя будет отменить.",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("delete_lot_"))
async def delete_lot_handler(callback: CallbackQuery):
    lot_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        if not lot:
            return await callback.answer("🍭 Лот уже удален!")
        if lot.owner_id != callback.from_user.id:
            return await callback.answer("❌ Это не твой лот!", show_alert=True)
            
        import logging
        logging.info(f"Lot deleted: ID={lot.id}, Title='{lot.title}', Owner={lot.owner_id}")
        
        await session.delete(lot)
        await session.commit()
        
    await callback.answer("✅ Лот успешно удален!", show_alert=True)
    await shop_my_lots_text(callback.message)

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
