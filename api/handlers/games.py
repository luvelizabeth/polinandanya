from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from api.config import config
from api.database.connection import async_session
from api.database.models import WordGuessGame, GameState
from sqlalchemy import select, update, delete
from datetime import datetime
import logging
import random
import json

router = Router()

# Word Guessing Game
@router.message(F.text == "🔮 Угадай слово")
async def word_guess_menu(message: Message, state: FSMContext):
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
                await message.answer(
                    "🔮 <b>УГАДАЙ СЛОВО</b>\n"
                    "─── ʚ 🔮 ɞ ───\n\n"
                    "Игра уже идет! Оба игрока получили свои слова.\n\n"
                    "Задавайте вопросы друг другу, чтобы угадать слово партнера!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")]
                    ])
                )
            else:
                await message.answer(
                    "🔮 <b>УГАДАЙ СЛОВО</b>\n"
                    "─── ʚ 🔮 ɞ ───\n\n"
                    "Игра в процессе! Ожидаем, когда оба игрока получат слова...",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")]
                    ])
                )
            return
    
    await message.answer(
        "🔮 <b>УГАДАЙ СЛОВО</b>\n"
        "─── ʚ 🔮 ɞ ───\n\n"
        "Каждый получит случайное слово и должен угадать слово партнера, задавая вопросы!\n\n"
        "Начать игру?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать игру", callback_data="start_word_guess")]
        ])
    )

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
                "Добавьте больше слов в базу данных."
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
        "Оба игрока получили свои слова. Задавайте вопросы друг другу!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Завершить игру", callback_data="end_word_guess")]
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
            [InlineKeyboardButton(text="🔄 Сыграть снова", callback_data="start_word_guess")]
        ])
    )
    await callback.answer()
