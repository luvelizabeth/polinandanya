from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from api.config import config

from aiogram.exceptions import TelegramBadRequest
import logging

router = Router()

class ReminderState(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()

@router.message(Command("ping"))
@router.message(F.text == "🧸 Заботливый пинг")
async def send_ping(message: Message, bot: Bot):
    partner_id = config.POLINA_ID if message.from_user.id == config.DANILA_ID else config.DANILA_ID
    sender_name = "Даня" if message.from_user.id == config.DANILA_ID else "Полина"
    
    text = f"🍓 <b>Заботливый пинг от {sender_name}!</b>\n\nТебе напоминают, что нужно попить водички, размять спину и улыбнуться! ✨💖"
    
    try:
        await bot.send_message(partner_id, text)
        await message.answer("✅ <b>Заботливый пинг успешно отправлен!</b>")
    except TelegramBadRequest as e:
        logging.error(f"Failed to send ping to {partner_id}: {e}")
        await message.answer(
            "🌸 <b>Ой, котик недоступен!</b>\n"
            "─── ʚ 🍓 ɞ ───\n\n"
            "Кажется, партнер еще не запустил бота или заблокировал его. "
            "Попроси его написать /start боту! ✨"
        )
    except Exception as e:
        logging.error(f"Unexpected error in send_ping: {e}")
        await message.answer("🍭 Произошла какая-то ошибка, попробуй еще раз позже!")

@router.message(ReminderState.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("В какое время напомнить? (в формате ЧЧ:ММ)")
    await state.set_state(ReminderState.waiting_for_time)

@router.message(ReminderState.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    await message.answer("⏳ Функция отложенных напоминаний адаптируется под новую архитектуру Vercel. Временно недоступна.")
    await state.clear()
