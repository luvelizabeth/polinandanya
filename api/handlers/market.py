import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from api.config import config
from api.database.connection import async_session
from api.database.models import Lot, User
from api.database.db_queries import get_or_create_user, update_balance

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
    await state.clear()
    await message.answer(
        "🎀 <b>НОВЫЙ ЛОТ</b>\n"
        "─── ʚ 🎀 ɞ ───\n\n"
        "Давай создадим что-то особенное! Пришли мне медиафайлы (фото, видео, ГС, кружки) или текст, который станет содержимым твоего лота.\n\n"
        "✨ <b>Важно:</b> можно отправить несколько файлов одного типа (например, 4 фото). Не смешивай разные типы контента в одном лоте!\n\n"
        "Когда закончишь отправлять файлы, нажми кнопку ниже 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Файлы отправлены", callback_data="finish_media")]
        ])
    )
    await state.set_state(CreateLotState.waiting_for_media)
    await state.update_data(media_list=[], media_type=None)

@router.message(CreateLotState.waiting_for_media)
async def process_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media_list", [])
    current_type = data.get("media_type")

    new_file_id = None
    new_type = None

    if message.photo:
        new_file_id = message.photo[-1].file_id
        new_type = "photo"
    elif message.video:
        new_file_id = message.video.file_id
        new_type = "video"
    elif message.voice:
        new_file_id = message.voice.file_id
        new_type = "voice"
    elif message.video_note:
        new_file_id = message.video_note.file_id
        new_type = "video_note"
    elif message.text:
        new_file_id = message.text
        new_type = "text"
    else:
        return await message.answer("🍭 <i>Ой, такой формат я пока не понимаю. Попробуй отправить что-то другое!</i>")

    if current_type and new_type != current_type:
        return await message.answer(f"⚠️ <b>Ошибка!</b>\nТы уже начал(а) добавлять <i>{current_type}</i>. Пожалуйста, не смешивай разные типы контента в одном лоте.")

    media_list.append(new_file_id)
    await state.update_data(media_list=media_list, media_type=new_type)
    
    if not message.media_group_id:
        await message.answer(f"✅ {new_type.capitalize()} №{len(media_list)} добавлено! Можешь отправить еще или нажать кнопку выше.")
    # For media groups, we don't spam messages to avoid rate limits and mess

@router.callback_query(F.data == "finish_media", CreateLotState.waiting_for_media)
async def finish_media(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("media_list"):
        return await callback.answer("⚠️ Ты не отправил(а) ни одного файла!", show_alert=True)
    
    await callback.message.answer(
        "🍰 <b>ЗАГОЛОВОК</b>\n"
        "─── ʚ 🍰 ɞ ───\n\n"
        "Придумай милое название для своего лота. Оно будет отображаться в вашем магазине чудес!"
    )
    await state.set_state(CreateLotState.waiting_for_title)
    await callback.answer()

@router.message(CreateLotState.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    if not message.text:
        return await message.answer("🍰 <i>Котик, пожалуйста, введи текстовое название для лота!</i>")
    
    await state.update_data(title=message.text)
    await message.answer(
        "🍰 <b>ОПИСАНИЕ</b>\n"
        "─── ʚ 🍰 ɞ ───\n\n"
        "Расскажи немного подробнее, что это за чудо? Твое описание поможет партнеру сделать выбор"
    )
    await state.set_state(CreateLotState.waiting_for_description)

@router.message(CreateLotState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    if not message.text:
        # If it's not text (e.g. another photo), just remind the user
        return await message.answer("🍰 <i>Напиши описание текстом, пожалуйста!</i>")

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
    if not message.text or not message.text.isdigit():
        return await message.answer("🐾 <i>Котик, введи, пожалуйста, только число!</i>")
    
    price = int(message.text)
    data = await state.get_data()
    
    # Debug logging for Vercel
    print(f"Creating lot: data={data}")
    
    if not data.get("title") or not data.get("media_list"):
        return await message.answer("⚠️ <b>Ошибка данных!</b>\nПохоже, произошел сбой при сохранении. Попробуй создать лот заново через /create_lot")

    async with async_session() as session:
        lot = Lot(
            owner_id=message.from_user.id, 
            title=data['title'], 
            description=data['description'],
            price=price, 
            media_file_id=json.dumps(data['media_list']), 
            media_type=data['media_type'],
            media_count=len(data['media_list'])
        )
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

@router.message(F.text == "🍭 Посмотреть лоты партнера")
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
    
    current_row = []
    for lot in lots:
        icon = type_icons.get(lot.media_type, "🍭")
        count_str = f"{lot.media_count} " if (lot.media_count or 1) > 1 else ""
        current_row.append(InlineKeyboardButton(text=f"{count_str}[{icon}] {lot.title}", callback_data=f"shop_view_{lot.id}"))
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []
    if current_row:
        buttons.append(current_row)
    
    await message.answer(
        "🍭 <b>ЛОТЫ ПАРТНЕРА</b>\n"
        "─── ʚ 🍭 ɞ ───\n\n"
        "Нажми на интересующий лот, чтобы узнать подробности и совершить покупку.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.message(F.text == "🍭 Мои лоты")
async def shop_my_lots_text(message: Message):
    async with async_session() as session:
        result = await session.execute(select(Lot).where(Lot.owner_id == message.from_user.id))
        lots = result.scalars().all()
        
    if not lots:
        return await message.answer(
            "🍭 <b>ТВОИ ЛОТЫ</b>\n"
            "─── ʚ 🍭 ɞ ───\n\n"
            "У тебя пока нет созданных лотов.\n"
            "Время что-нибудь придумать! 💖"
        )
        
    buttons = []
    type_icons = {"photo": "🖼️", "video": "🎬", "voice": "🎙️", "video_note": "⭕", "text": "📝"}
    
    current_row = []
    for lot in lots:
        icon = type_icons.get(lot.media_type, "🎀")
        count_str = f"{lot.media_count} " if (lot.media_count or 1) > 1 else ""
        current_row.append(InlineKeyboardButton(text=f"{count_str}[{icon}] {lot.title}", callback_data=f"shop_view_my_{lot.id}"))
        if len(current_row) == 2:
            buttons.append(current_row)
            current_row = []
    if current_row:
        buttons.append(current_row)
    
    await message.answer(
        "🍭 <b>ТВОИ ЛОТЫ</b>\n"
        "─── ʚ 🍭 ɞ ───\n\n"
        "Твои активные и проданные предложения.",
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
async def shop_view_lot(callback: CallbackQuery, bot: Bot):
    is_mine = callback.data.startswith("shop_view_my_")
    lot_id = int(callback.data.replace("shop_view_my_", "").replace("shop_view_", ""))
    
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        
    if not lot:
        return await callback.answer("🍭 Лот не найден!", show_alert=True)
        
    type_names = {"photo": "Фотографии 🖼️", "video": "Видео 🎬", "voice": "Голосовые 🎙️", "video_note": "Кружки ⭕", "text": "Тексты 📝"}
    m_type = type_names.get(lot.media_type, "Контент 🍭")
    
    text = (
        f"✨ <b>ИНФОРМАЦИЯ О ЛОТЕ</b>\n"
        f"─── ʚ 🍭 ɞ ───\n\n"
        f"🏷 <b>Название:</b> {lot.title}\n"
        f"📝 <b>Описание:</b> {lot.description}\n"
        f"📂 <b>Тип:</b> {m_type} ({lot.media_count} шт.)\n"
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

@router.callback_query(F.data.startswith("buy_lot_"))
async def buy_lot(callback: CallbackQuery, bot: Bot):
    lot_id = int(callback.data.split("_")[2])
    buyer_id = callback.from_user.id
    
    async with async_session() as session:
        lot = await session.get(Lot, lot_id)
        if not lot or not lot.is_active:
            return await callback.answer("🍭 Этот лот уже недоступен или продан!", show_alert=True)
            
        buyer = await get_or_create_user(session, buyer_id)
        if buyer.balance < lot.price:
            return await callback.answer(f"🐾 Недостаточно Лапкоинов! Нужно еще {lot.price - buyer.balance}.", show_alert=True)
            
        # Deduct balance from buyer and deactivate lot
        buyer.balance -= lot.price
        
        # Give full price to the seller (no commission for a private bot for a girlfriend!)
        seller = await get_or_create_user(session, lot.owner_id)
        seller.balance += lot.price
        
        lot.is_active = False
        await session.commit()
        
    await callback.answer("🎉 Поздравляю с покупкой! Сейчас пришлю содержимое.", show_alert=True)
    
    # Update the shop view message
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ К витрине партнера", callback_data="shop_partner_lots")]])
    await callback.message.edit_text(
        f"✅ <b>ЛОТ ВЫКУПЛЕН!</b>\n"
        f"─── ʚ 🍭 ɞ ───\n\n"
        f"Ты успешно приобрел(а) лот «{lot.title}» за {lot.price} 🐾\n\n"
        f"Содержимое лота отправлено тебе ниже! 👇",
        reply_markup=kb
    )
    
    # Send content
    try:
        media_ids = json.loads(lot.media_file_id)
        if not isinstance(media_ids, list):
            media_ids = [media_ids]
    except:
        # Fallback for old lots that stored a single string
        media_ids = [lot.media_file_id]

    if lot.media_type == "text":
        for t in media_ids:
            await bot.send_message(chat_id=buyer_id, text=f"📝 <b>Текст из лота:</b>\n\n{t}")
    elif lot.media_type == "photo":
        if len(media_ids) > 1:
            media = [InputMediaPhoto(media=m) for m in media_ids]
            await bot.send_media_group(chat_id=buyer_id, media=media)
        else:
            await bot.send_photo(chat_id=buyer_id, photo=media_ids[0], caption=f"🖼️ Лот «{lot.title}»")
    elif lot.media_type == "video":
        if len(media_ids) > 1:
            media = [InputMediaVideo(media=m) for m in media_ids]
            await bot.send_media_group(chat_id=buyer_id, media=media)
        else:
            await bot.send_video(chat_id=buyer_id, video=media_ids[0], caption=f"🎬 Лот «{lot.title}»")
    elif lot.media_type == "voice":
        for m in media_ids:
            await bot.send_voice(chat_id=buyer_id, voice=m)
    elif lot.media_type == "video_note":
        for m in media_ids:
            await bot.send_video_note(chat_id=buyer_id, video_note=m)

    # Notify the seller
    await bot.send_message(
        lot.owner_id, 
        f"🔔 <b>ТВОЙ ЛОТ КУПЛЕН!</b>\n"
        f"─── ʚ 🍭 ɞ ───\n\n"
        f"Партнер выкупил лот «{lot.title}»!\n"
        f"💰 На твой баланс зачислено: <b>{lot.price}</b> 🐾"
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_lot(callback: CallbackQuery):
    lot_id = int(callback.data.split("_")[2])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_lot_{lot_id}")],
        [InlineKeyboardButton(text="❌ Нет, оставить", callback_data=f"shop_view_my_{lot_id}")]
    ])
    await callback.message.edit_text(
        "⚠️ <b>ПОДТВЕРЖДЕНИЕ</b>\n"
        "─── ʚ 🗑 ɞ ───\n\n"
        "Ты действительно хочешь удалить этот лот?\n"
        "Это действие нельзя будет отменить.",
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
            
        await session.delete(lot)
        await session.commit()
        
    await callback.answer("✅ Лот успешно удален!")
    await callback.message.edit_text(
        "💖 <b>УДАЛЕНО</b>\n"
        "─── ʚ 💖 ɞ ───\n\n"
        "Лот успешно удален из твоего магазина чудес.",
        reply_markup=None
    )
