from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
from api.handlers.games import get_games_keyboard

router = Router()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍬 Мой баланс")],
            [KeyboardButton(text="🧸 Сыграть в дилеммы"), KeyboardButton(text="☁️ Наши сновидения")],
            [KeyboardButton(text="🍯 Копилка цитат"), KeyboardButton(text="🍪 Заботливый пинг")],
            [KeyboardButton(text="🎮 Игры для пары")]
        ], resize_keyboard=True
    )

def get_dreams_keyboard_nav():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📖 Просмотреть сохраненные сны")],
            [KeyboardButton(text="✍️ Добавить новый сон")],
            [KeyboardButton(text="🌸 Назад")]
        ], resize_keyboard=True
    )

def get_quotes_keyboard_nav():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Просмотреть цитаты")],
            [KeyboardButton(text="✍️ Добавить цитату")],
            [KeyboardButton(text="🌸 Назад")]
        ], resize_keyboard=True
    )

@router.message(Command("start"))
@router.message(Command("menu"))
@router.message(F.text == "🌸 Назад")
async def show_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🌸 <b>ГЛАВНОЕ МЕНЮ</b>\n"
        "─── ʚ 🌸 ɞ ───\n\n"
        "Добро пожаловать! Здесь собраны все функции для нашего общения. Выбирай раздел ниже\n\n"
        "🌸 <i>Твой уютный помощник готов к работе!</i>",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🎮 Игры для пары")
async def show_games(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎮 <b>ИГРЫ ДЛЯ ПАРЫ</b>\n"
        "─── ʚ 🎮 ɞ ───\n\n"
        "Выбери игру:",
        reply_markup=get_games_keyboard()
    )
