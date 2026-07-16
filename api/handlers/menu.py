from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

router = Router()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Мой баланс")],
            [KeyboardButton(text="🛍️ Магазин чудес"), KeyboardButton(text="🎁 Создать лот")],
            [KeyboardButton(text="🎭 Сыграть в дилеммы"), KeyboardButton(text="☁️ Наши сновидения")],
            [KeyboardButton(text="💬 Копилка цитат"), KeyboardButton(text="🫂 Заботливый пинг")]
        ], resize_keyboard=True
    )

def get_shop_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Посмотреть лоты партнера")],
            [KeyboardButton(text="📦 Мои лоты")],
            [KeyboardButton(text="⬅️ Назад")]
        ], resize_keyboard=True
    )

def get_dreams_keyboard_nav():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📖 Просмотреть сохраненные сны")],
            [KeyboardButton(text="✍️ Добавить новый сон")],
            [KeyboardButton(text="⬅️ Назад")]
        ], resize_keyboard=True
    )

def get_quotes_keyboard_nav():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Просмотреть цитаты")],
            [KeyboardButton(text="✍️ Добавить цитату")],
            [KeyboardButton(text="⬅️ Назад")]
        ], resize_keyboard=True
    )

@router.message(Command("start"))
@router.message(Command("menu"))
@router.message(F.text == "⬅️ Назад")
async def show_menu(message: Message):
    await message.answer(
        "👋 <b>Добро пожаловать в главное меню!</b>\n\n"
        "Выбирай, чем хочешь заняться сегодня. Здесь собраны все наши функции — от магазина и дилемм до снов и цитат.",
        reply_markup=get_main_keyboard()
    )
