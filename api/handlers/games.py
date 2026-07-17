from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from api.config import config
from api.database.connection import async_session
from api.database.models import TruthOrDare, WordGuessGame, GameState
from sqlalchemy import select, update, delete
from datetime import datetime
import logging
import random
import json

router = Router()

class TruthOrDareState(StatesGroup):
    choosing_category = State()
    choosing_difficulty = State()
    showing_question = State()

class WordGuessState(StatesGroup):
    waiting_for_answer = State()
    asking_question = State()

def get_games_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Правда или Действие", callback_data="truth_or_dare")],
        [InlineKeyboardButton(text="🔮 Угадай слово", callback_data="word_guess")],
        [InlineKeyboardButton(text="🌸 Назад", callback_data="back_to_menu")]
    ])

def get_category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💕 Романтика", callback_data="cat_romance")],
        [InlineKeyboardButton(text="📜 Прошлое", callback_data="cat_past")],
        [InlineKeyboardButton(text="🔄 Привычки", callback_data="cat_habits")],
        [InlineKeyboardButton(text="✨ Фантазии", callback_data="cat_fantasy")],
        [InlineKeyboardButton(text="😄 Веселое", callback_data="cat_fun")],
        [InlineKeyboardButton(text="🌸 Случайная", callback_data="cat_random")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
    ])

def get_difficulty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Легко", callback_data="diff_easy")],
        [InlineKeyboardButton(text="🟡 Средне", callback_data="diff_medium")],
        [InlineKeyboardButton(text="🔴 Сложно", callback_data="diff_hard")],
        [InlineKeyboardButton(text="🌸 Случайная", callback_data="diff_random")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_category")]
    ])

def get_truth_or_dare_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 ПРАВДА", callback_data="type_truth")],
        [InlineKeyboardButton(text="🔥 ДЕЙСТВИЕ", callback_data="type_dare")],
        [InlineKeyboardButton(text="🎲 Случайно", callback_data="type_random")],
        [InlineKeyboardButton(text="🌸 Назад", callback_data="back_to_games")]
    ])

def get_tod_action_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнено!", callback_data="tod_done")],
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="tod_skip")],
        [InlineKeyboardButton(text="🔄 Еще раз", callback_data="tod_again")],
        [InlineKeyboardButton(text="🌸 Выход", callback_data="back_to_games")]
    ])

@router.callback_query(F.data == "games")
async def games_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎮 <b>ИГРЫ ДЛЯ ПАРЫ</b>\n"
        "─── ʚ 🎮 ɞ ───\n\n"
        "Выбери игру:",
        reply_markup=get_games_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "truth_or_dare")
async def truth_or_dare_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎯 <b>ПРАВДА ИЛИ ДЕЙСТВИЕ</b>\n"
        "─── ʚ 🎯 ɞ ───\n\n"
        "Классическая игра для пары! Выбирай категорию и сложность, получи задание или вопрос.\n\n"
        "Что выбираешь?",
        reply_markup=get_truth_or_dare_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("type_"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    type_map = {"type_truth": "truth", "type_dare": "dare", "type_random": None}
    tod_type = type_map[callback.data]
    
    await state.update_data(tod_type=tod_type)
    await callback.message.edit_text(
        "📁 <b>Выбери категорию:</b>",
        reply_markup=get_category_keyboard()
    )
    await state.set_state(TruthOrDareState.choosing_category)
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"), TruthOrDareState.choosing_category)
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    if category == "random":
        category = None
    
    await state.update_data(category=category)
    await callback.message.edit_text(
        "⚡ <b>Выбери сложность:</b>",
        reply_markup=get_difficulty_keyboard()
    )
    await state.set_state(TruthOrDareState.choosing_difficulty)
    await callback.answer()

@router.callback_query(F.data.startswith("diff_"), TruthOrDareState.choosing_difficulty)
async def choose_difficulty(callback: CallbackQuery, state: FSMContext):
    difficulty = callback.data.split("_")[1]
    if difficulty == "random":
        difficulty = None
    
    data = await state.get_data()
    tod_type = data.get('tod_type')
    category = data.get('category')
    
    async with async_session() as session:
        query = select(TruthOrDare).where(TruthOrDare.is_used == False)
        
        if tod_type:
            query = query.where(TruthOrDare.type == tod_type)
        if category:
            query = query.where(TruthOrDare.category == category)
        if difficulty:
            query = query.where(TruthOrDare.difficulty == difficulty)
        
        result = await session.execute(query)
        questions = result.scalars().all()
        
        if not questions:
            await callback.message.edit_text(
                "😿 <b>Нет вопросов в этой категории!</b>\n\n"
                "Попробуй другую категорию или сложность.",
                reply_markup=get_truth_or_dare_keyboard()
            )
            await state.clear()
            await callback.answer()
            return
        
        question = random.choice(questions)
        question.is_used = True
        await session.commit()
    
    type_emoji = "🎯" if question.type == "truth" else "🔥"
    type_text = "ПРАВДА" if question.type == "truth" else "ДЕЙСТВИЕ"
    
    await callback.message.edit_text(
        f"{type_emoji} <b>{type_text}</b>\n"
        f"─── ʚ {type_emoji} ɞ ───\n\n"
        f"{question.text}\n\n"
        f"📁 Категория: {question.category}\n"
        f"⚡ Сложность: {question.difficulty}",
        reply_markup=get_tod_action_keyboard()
    )
    await state.set_state(TruthOrDareState.showing_question)
    await callback.answer()

@router.callback_query(F.data == "tod_done", TruthOrDareState.showing_question)
async def tod_done(callback: CallbackQuery, state: FSMContext, bot: Bot):
    partner_id = config.POLINA_ID if callback.from_user.id == config.DANILA_ID else config.DANILA_ID
    
    try:
        await bot.send_message(partner_id, "🎉 <b>Партнер выполнил задание!</b>\nМолодец! 🍓")
        await callback.message.edit_text(
            "✅ <b>Отлично!</b>\n\n"
            "Партнер уведомлен о твоем успехе! 🎉",
            reply_markup=get_truth_or_dare_keyboard()
        )
    except Exception as e:
        logging.error(f"Failed to send tod done notification: {e}")
        await callback.message.edit_text(
            "✅ <b>Отлично!</b>\n\n"
            "Задание выполнено!",
            reply_markup=get_truth_or_dare_keyboard()
        )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "tod_skip", TruthOrDareState.showing_question)
async def tod_skip(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⏭️ <b>Пропущено!</b>\n\n"
        "Ничего страшного, в следующий раз повезет больше! 😊",
        reply_markup=get_truth_or_dare_keyboard()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "tod_again", TruthOrDareState.showing_question)
async def tod_again(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tod_type = data.get('tod_type')
    category = data.get('category')
    difficulty = data.get('difficulty')
    
    async with async_session() as session:
        query = select(TruthOrDare).where(TruthOrDare.is_used == False)
        
        if tod_type:
            query = query.where(TruthOrDare.type == tod_type)
        if category:
            query = query.where(TruthOrDare.category == category)
        if difficulty:
            query = query.where(TruthOrDare.difficulty == difficulty)
        
        result = await session.execute(query)
        questions = result.scalars().all()
        
        if not questions:
            await callback.message.edit_text(
                "😿 <b>Вопросы закончились!</b>\n\n"
                "Попробуй другую категорию.",
                reply_markup=get_truth_or_dare_keyboard()
            )
            await state.clear()
            await callback.answer()
            return
        
        question = random.choice(questions)
        question.is_used = True
        await session.commit()
    
    type_emoji = "🎯" if question.type == "truth" else "🔥"
    type_text = "ПРАВДА" if question.type == "truth" else "ДЕЙСТВИЕ"
    
    await callback.message.edit_text(
        f"{type_emoji} <b>{type_text}</b>\n"
        f"─── ʚ {type_emoji} ɞ ───\n\n"
        f"{question.text}\n\n"
        f"📁 Категория: {question.category}\n"
        f"⚡ Сложность: {question.difficulty}",
        reply_markup=get_tod_action_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_category")
async def back_to_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📁 <b>Выбери категорию:</b>",
        reply_markup=get_category_keyboard()
    )
    await state.set_state(TruthOrDareState.choosing_category)
    await callback.answer()

@router.callback_query(F.data == "back_to_games")
async def back_to_games(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎮 <b>ИГРЫ ДЛЯ ПАРЫ</b>\n"
        "─── ʚ 🎮 ɞ ───\n\n"
        "Выбери игру:",
        reply_markup=get_games_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    from api.handlers.menu import get_main_keyboard
    await state.clear()
    await callback.message.edit_text(
        "🌸 <b>ГЛАВНОЕ МЕНЮ</b>\n"
        "─── ʚ 🌸 ɞ ───\n\n"
        "Добро пожаловать! Здесь собраны все функции для нашего общения. Выбирай раздел ниже\n\n"
        "🌸 <i>Твой уютный помощник готов к работе!</i>",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# Word Guessing Game
@router.callback_query(F.data == "word_guess")
async def word_guess_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Check if game is already active
    async with async_session() as session:
        game_state = await session.execute(
            select(GameState).where(GameState.id == "word_guess")
        )
        game = game_state.scalar_one_or_none()
        
        if game and game.is_active:
            game_data = json.loads(game.data)
            player1_word = game_data.get("player1_word")
            player2_word = game_data.get("player2_word")
            
            if player1_word and player2_word:
                await callback.message.edit_text(
                    "🔮 <b>УГАДАЙ СЛОВО</b>\n"
                    "─── ʚ 🔮 ɞ ───\n\n"
                    "Игра уже идет! Оба игрока получили свои слова.\n\n"
                    "Задавайте вопросы друг другу, чтобы угадать слово партнера!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
                    ])
                )
            else:
                await callback.message.edit_text(
                    "🔮 <b>УГАДАЙ СЛОВО</b>\n"
                    "─── ʚ 🔮 ɞ ───\n\n"
                    "Игра в процессе! Ожидаем, когда оба игрока получат слова...",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
                    ])
                )
            await callback.answer()
            return
    
    await callback.message.edit_text(
        "🔮 <b>УГАДАЙ СЛОВО</b>\n"
        "─── ʚ 🔮 ɞ ───\n\n"
        "Каждый получит случайное слово и должен угадать слово партнера, задавая вопросы!\n\n"
        "Начать игру?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать игру", callback_data="start_word_guess")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "start_word_guess")
async def start_word_guess(callback: CallbackQuery, state: FSMContext, bot: Bot):
    async with async_session() as session:
        # Get random words
        result = await session.execute(
            select(WordGuessGame).where(WordGuessGame.is_used == False)
        )
        words = result.scalars().all()
        
        if len(words) < 2:
            await callback.message.edit_text(
                "😿 <b>Недостаточно слов!</b>\n\n"
                "Добавьте больше слов в базу данных.",
                reply_markup=get_games_keyboard()
            )
            await callback.answer()
            return
        
        selected_words = random.sample(words, 2)
        for word in selected_words:
            word.is_used = True
        
        # Initialize game state
        game_state = GameState(
            id="word_guess",
            is_active=True,
            data=json.dumps({
                "player1_id": config.DANILA_ID,
                "player1_word": selected_words[0].word,
                "player2_id": config.POLINA_ID,
                "player2_word": selected_words[1].word,
                "questions": {},
                "started_at": datetime.utcnow().isoformat()
            })
        )
        session.add(game_state)
        await session.commit()
        
        # Send words to players
        try:
            await bot.send_message(
                config.DANILA_ID,
                f"🔮 <b>ТВОЕ СЛОВО:</b> {selected_words[0].word}\n\n"
                f"Задавай вопросы Полине, чтобы угадать её слово!"
            )
            await bot.send_message(
                config.POLINA_ID,
                f"🔮 <b>ТВОЕ СЛОВО:</b> {selected_words[1].word}\n\n"
                f"Задавай вопросы Дане, чтобы угадать его слово!"
            )
        except Exception as e:
            logging.error(f"Failed to send word guess messages: {e}")
    
    await callback.message.edit_text(
        "🚀 <b>Игра началась!</b>\n\n"
        "Оба игрока получили свои слова. Задавайте вопросы друг другу!\n\n"
        "Когда кто-то угадает слово, напишите /guess для завершения.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "end_word_guess")
async def end_word_guess(callback: CallbackQuery, state: FSMContext, bot: Bot):
    async with async_session() as session:
        await session.execute(
            update(GameState).where(GameState.id == "word_guess").values(is_active=False)
        )
        await session.commit()
    
    try:
        await bot.send_message(config.DANILA_ID, "🔮 Игра 'Угадай слово' завершена!")
        await bot.send_message(config.POLINA_ID, "🔮 Игра 'Угадай слово' завершена!")
    except Exception as e:
        logging.error(f"Failed to send end game notification: {e}")
    
    await callback.message.edit_text(
        "🔮 <b>Игра завершена!</b>\n\n"
        "Хотите сыграть еще раз?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сыграть снова", callback_data="start_word_guess")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_games")]
        ])
    )
    await callback.answer()
