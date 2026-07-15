from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

router = Router()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ежедневный бонус"), KeyboardButton(text="Баланс")],
            [KeyboardButton(text="Магазин"), KeyboardButton(text="Создать лот")],
            [KeyboardButton(text="Сыграть в дилеммы")],
            [KeyboardButton(text="Записать сон"), KeyboardButton(text="Наши сны")],
            [KeyboardButton(text="Заботливый пинг")],
            [KeyboardButton(text="Добавить цитату"), KeyboardButton(text="Посмотреть цитаты")]
        ], resize_keyboard=True
    )

@router.message(Command("start"))
@router.message(Command("menu"))
async def show_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())
