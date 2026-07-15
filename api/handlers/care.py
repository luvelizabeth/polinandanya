from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

class ReminderState(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()

@router.message(Command("ping"))
@router.message(F.text == "Заботливый пинг")
async def start_reminder(message: Message, state: FSMContext):
    await message.answer("Что ты хочешь напомнить партнеру?")
    await state.set_state(ReminderState.waiting_for_text)

@router.message(ReminderState.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("В какое время напомнить? (в формате ЧЧ:ММ)")
    await state.set_state(ReminderState.waiting_for_time)

@router.message(ReminderState.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext):
    await message.answer("⏳ Функция отложенных напоминаний адаптируется под новую архитектуру Vercel. Временно недоступна.")
    await state.clear()
