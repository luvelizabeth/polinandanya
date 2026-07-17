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
    waiting_for_time = State()

def get_care_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍓 Быстрый пинг", callback_data="fast_ping")],
        [InlineKeyboardButton(text="⏰ Запланировать напоминание", callback_data="add_reminder")],
        [InlineKeyboardButton(text="📋 Мои напоминания", callback_data="list_reminders")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
    ])

@router.message(Command("care"))
@router.message(F.text == "🍪 Заботливый пинг")
async def care_menu(message: Message):
    await message.answer(
        "🍪 <b>ЗАБОТЛИВЫЙ ПИНГ</b>\n"
        "─── ʚ 🍪 ɞ ───\n\n"
        "Здесь ты можешь отправить быстрый «кусь» партнеру или запланировать важное напоминание на потом. ✨\n\n"
        "Что выберешь?",
        reply_markup=get_care_keyboard()
    )

@router.callback_query(F.data == "fast_ping")
async def fast_ping_cb(callback: CallbackQuery, bot: Bot):
    partner_id = config.POLINA_ID if callback.from_user.id == config.DANILA_ID else config.DANILA_ID
    sender_name = "Даня" if callback.from_user.id == config.DANILA_ID else "Полина"
    
    text = f"🍓 <b>Заботливый пинг от {sender_name}!</b>\n\nТебе напоминают, что нужно попить водички, размять спину и улыбнуться! ✨💖"
    
    try:
        await bot.send_message(partner_id, text)
        await callback.answer("Пинг отправлен! 🍓")
    except Exception:
        await callback.answer("Не удалось отправить пинг 😿", show_alert=True)

@router.callback_query(F.data == "add_reminder")
async def add_reminder_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ <b>Создание напоминания</b>\n\n"
        "Введи текст сообщения, которое получит партнер:"
    )
    await state.set_state(ReminderState.waiting_for_text)
    await callback.answer()

@router.message(ReminderState.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        "⏰ <b>Когда отправить?</b>\n\n"
        "Введи время в формате <code>ЧЧ:ММ</code> (например, 22:00).\n"
        "<i>Напоминание будет запланировано на ближайшее такое время.</i>"
    )
    await state.set_state(ReminderState.waiting_for_time)

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
        f"📅 <b>Время:</b> {target_time.strftime('%H:%M')}\n"
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
        buttons.append([InlineKeyboardButton(text=f"🗑 Удалить {local_time.strftime('%H:%M')}", callback_data=f"del_rem_{r.id}")])
    
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

@router.callback_query(F.data == "back_to_care")
async def back_to_care_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        "🍪 <b>ЗАБОТЛИВЫЙ ПИНГ</b>\n"
        "─── ʚ 🍪 ɞ ───\n\n"
        "Здесь ты можешь отправить быстрый «кусь» партнеру или запланировать важное напоминание на потом. ✨\n\n"
        "Что выберешь?",
        reply_markup=get_care_keyboard()
    )
    await callback.answer()
