from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from api.config import config
from api.database.connection import async_session
from api.database.models import Reminder
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import logging
import re

from aiogram.exceptions import TelegramBadRequest

router = Router()

class ReminderState(StatesGroup):
    waiting_for_text = State()
    waiting_for_type = State()
    waiting_for_time = State()
    editing_text = State()
    editing_time = State()

def get_care_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Создать новое напоминание", callback_data="add_reminder")],
        [InlineKeyboardButton(text="📋 Мои активные напоминания", callback_data="list_reminders")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
    ])

def get_reminder_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить прямо сейчас", callback_data="send_now")],
        [InlineKeyboardButton(text="⏰ Запланировать на время", callback_data="send_later")],
        [InlineKeyboardButton(text="🌸 Отмена", callback_data="back_to_care")]
    ])

@router.message(Command("care"))
@router.message(F.text == "🍪 Заботливый пинг")
async def care_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🍪 <b>ЗАБОТЛИВЫЙ ПИНГ</b>\n"
        "─── ʚ 🍪 ɞ ───\n\n"
        "Здесь ты можешь проявить заботу о партнере: отправить сообщение прямо сейчас или запланировать его на конкретное время. ✨\n\n"
        "Выбери действие:",
        reply_markup=get_care_keyboard()
    )

@router.callback_query(F.data == "add_reminder")
async def add_reminder_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ <b>Что передать партнеру?</b>\n\n"
        "Введи текст сообщения. Это может быть что-то милое, напоминание о воде или просто «люблю»."
    )
    await state.set_state(ReminderState.waiting_for_text)
    await callback.answer()

@router.message(ReminderState.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        "✨ <b>Текст принят!</b>\n\n"
        "Когда мы отправим это сообщение?",
        reply_markup=get_reminder_type_keyboard()
    )
    await state.set_state(ReminderState.waiting_for_type)

@router.callback_query(F.data == "send_now", ReminderState.waiting_for_type)
async def send_now_cb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text = data['text']
    
    partner_id = config.POLINA_ID if callback.from_user.id == config.DANILA_ID else config.DANILA_ID
    sender_name = "Дани" if callback.from_user.id == config.DANILA_ID else "Полины"
    
    msg_text = (
        f"💌 <b>Заботливое напоминание от {sender_name}!</b>\n"
        f"─── ʚ ✨ ɞ ───\n\n"
        f"{text}"
    )
    
    try:
        await bot.send_message(partner_id, msg_text)
        await callback.message.edit_text(f"✅ <b>Отправлено!</b>\n\nПартнер получил твое сообщение: <i>«{text}»</i>")
        await callback.answer("Успешно отправлено! 🍓")
    except Exception as e:
        logging.error(f"Failed to send immediate ping: {e}")
        await callback.message.edit_text("❌ <b>Ошибка</b>\nНе удалось отправить сообщение. Возможно, партнер заблокировал бота.")
        await callback.answer("Ошибка отправки 😿", show_alert=True)
    
    await state.clear()

@router.callback_query(F.data == "send_later", ReminderState.waiting_for_type)
async def send_later_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⏰ <b>На какое время запланировать?</b>\n\n"
        "Введи время в формате <code>ЧЧ:ММ</code> (например, 22:00).\n"
        "<i>Я отправлю его в ближайшие указанные часы и минуты.</i>"
    )
    await state.set_state(ReminderState.waiting_for_time)
    await callback.answer()

@router.message(ReminderState.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        return await message.answer("⚠️ Неверный формат. Пожалуйста, введи время как <code>ЧЧ:ММ</code> (например, 09:30).")

    hours, minutes = map(int, time_str.split(":"))
    now = datetime.utcnow() + timedelta(hours=3) # MSK
    target_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    
    if target_time <= now:
        target_time += timedelta(days=1)

    data = await state.get_data()
    text = data['text']
    partner_id = config.POLINA_ID if message.from_user.id == config.DANILA_ID else config.DANILA_ID

    async with async_session() as session:
        new_reminder = Reminder(
            sender_id=message.from_user.id,
            receiver_id=partner_id,
            text=text,
            send_at=target_time - timedelta(hours=3) # Store as UTC
        )
        session.add(new_reminder)
        await session.commit()

    await message.answer(
        f"✅ <b>Напоминание запланировано!</b>\n\n"
        f"⏰ <b>Время:</b> {target_time.strftime('%H:%M')}\n"
        f"📝 <b>Текст:</b> {text}\n\n"
        f"Я отправлю его партнеру точно в срок! ✨"
    )
    await state.clear()

@router.callback_query(F.data == "list_reminders")
async def list_reminders_cb(callback: CallbackQuery):
    async with async_session() as session:
        res = await session.execute(
            select(Reminder).where(
                Reminder.sender_id == callback.from_user.id,
                Reminder.is_sent == False
            ).order_by(Reminder.send_at)
        )
        reminders = res.scalars().all()

    if not reminders:
        return await callback.answer("У тебя нет активных напоминаний! 📋", show_alert=True)

    text = "📋 <b>ТВОИ НАПОМИНАНИЯ</b>\n\n"
    buttons = []
    for r in reminders:
        local_time = r.send_at + timedelta(hours=3)
        text += f"⏰ <b>{local_time.strftime('%H:%M')}</b>: {r.text[:30]}...\n"
        buttons.append([
            InlineKeyboardButton(text=f"✏️ Текст", callback_data=f"edit_text_{r.id}"),
            InlineKeyboardButton(text=f"⏰ Время", callback_data=f"edit_time_{r.id}"),
            InlineKeyboardButton(text=f"🗑", callback_data=f"del_rem_{r.id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="🌸 Назад", callback_data="back_to_care")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("del_rem_"))
async def delete_reminder_cb(callback: CallbackQuery):
    rem_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Reminder).where(Reminder.id == rem_id, Reminder.sender_id == callback.from_user.id))
        await session.commit()
    
    await callback.answer("Напоминание удалено! 🗑")
    await list_reminders_cb(callback)

@router.callback_query(F.data.startswith("edit_text_"))
async def edit_reminder_text_cb(callback: CallbackQuery, state: FSMContext):
    rem_id = int(callback.data.split("_")[2])
    await state.update_data(reminder_id=rem_id)
    await callback.message.edit_text(
        "✏️ <b>Изменить текст напоминания</b>\n\n"
        "Введи новый текст сообщения:"
    )
    await state.set_state(ReminderState.editing_text)
    await callback.answer()

@router.message(ReminderState.editing_text)
async def process_edit_text(message: Message, state: FSMContext):
    data = await state.get_data()
    rem_id = data['reminder_id']
    
    async with async_session() as session:
        res = await session.execute(
            select(Reminder).where(
                Reminder.id == rem_id,
                Reminder.sender_id == message.from_user.id
            )
        )
        reminder = res.scalar_one_or_none()
        
        if not reminder:
            await message.answer("❌ Напоминание не найдено или уже удалено")
            await state.clear()
            return
        
        reminder.text = message.text
        await session.commit()
    
    await message.answer(
        f"✅ <b>Текст обновлен!</b>\n\n"
        f"📝 <b>Новый текст:</b> {message.text}"
    )
    await state.clear()

@router.callback_query(F.data.startswith("edit_time_"))
async def edit_reminder_time_cb(callback: CallbackQuery, state: FSMContext):
    rem_id = int(callback.data.split("_")[2])
    await state.update_data(reminder_id=rem_id)
    await callback.message.edit_text(
        "⏰ <b>Изменить время напоминания</b>\n\n"
        "Введи новое время в формате <code>ЧЧ:ММ</code> (например, 22:00)."
    )
    await state.set_state(ReminderState.editing_time)
    await callback.answer()

@router.message(ReminderState.editing_time)
async def process_edit_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        return await message.answer("⚠️ Неверный формат. Пожалуйста, введи время как <code>ЧЧ:ММ</code> (например, 09:30).")

    hours, minutes = map(int, time_str.split(":"))
    now = datetime.utcnow() + timedelta(hours=3) # MSK
    target_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    
    if target_time <= now:
        target_time += timedelta(days=1)

    data = await state.get_data()
    rem_id = data['reminder_id']
    
    async with async_session() as session:
        res = await session.execute(
            select(Reminder).where(
                Reminder.id == rem_id,
                Reminder.sender_id == message.from_user.id
            )
        )
        reminder = res.scalar_one_or_none()
        
        if not reminder:
            await message.answer("❌ Напоминание не найдено или уже удалено")
            await state.clear()
            return
        
        reminder.send_at = target_time - timedelta(hours=3) # Store as UTC
        await session.commit()
    
    await message.answer(
        f"✅ <b>Время обновлено!</b>\n\n"
        f"⏰ <b>Новое время:</b> {target_time.strftime('%H:%M')}"
    )
    await state.clear()

@router.callback_query(F.data == "back_to_care")
async def back_to_care_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🍪 <b>ЗАБОТЛИВЫЙ ПИНГ</b>\n"
        "─── ʚ 🍪 ɞ ───\n\n"
        "Здесь ты можешь проявить заботу о партнере: отправить сообщение прямо сейчас или запланировать его на конкретное время. ✨\n\n"
        "Выбери действие:",
        reply_markup=get_care_keyboard()
    )
    await callback.answer()
