from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

router = Router()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Мой баланс")],
            [KeyboardButton(text="🛍️ Магазин чудес"), KeyboardButton(text="🎁 Создать лот")],
            [KeyboardButton(text="🎭 Сыграть в дилеммы")],
            [KeyboardButton(text="☁️ Наши сновидения")],
            [KeyboardButton(text="💬 Копилка цитат")],
            [KeyboardButton(text="🫂 Заботливый пинг")]
        ], resize_keyboard=True
    )

@router.message(Command("start"))
@router.message(Command("menu"))
async def show_menu(message: Message):
    await message.answer(
        "👋 <b>Добро пожаловать в главное меню!</b>\n\n"
        "Выбирай, чем хочешь заняться сегодня. Здесь собраны все наши функции — от магазина и дилемм до снов и цитат.",
        reply_markup=get_main_keyboard()
    )
