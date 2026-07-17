import json
import pymorphy3
from aiogram import Router, F, Bot
from aiogram.types import Message

from api.config import config
from api.database.connection import async_session
from api.database.db_queries import get_game_state

router = Router()
morph = pymorphy3.MorphAnalyzer()

@router.message(F.text)
async def handle_association_answer(message: Message, bot: Bot):
    user_id = message.from_user.id
    async with async_session() as session:
        state = await get_game_state(session, "association")
        if state.is_active:
            data = json.loads(state.data)
            if str(user_id) not in data.get("answers", {}):
                raw_text = message.text.lower().strip().split()[0]
                parsed = morph.parse(raw_text)[0]
                normalized = parsed.normal_form
                
                if "answers" not in data:
                    data["answers"] = {}
                data["answers"][str(user_id)] = {"raw": message.text, "normalized": normalized}
                state.data = json.dumps(data)
                await session.commit()
                
                await message.answer("Ответ принят! Ждем партнера...")
                
                if len(data["answers"]) == 2:
                    ans_danila = data["answers"].get(str(config.DANILA_ID))
                    ans_polina = data["answers"].get(str(config.POLINA_ID))
                    word = data.get("word", "")
                    
                    state.is_active = False
                    state.data = "{}"
                    
                    if ans_danila["normalized"] == ans_polina["normalized"]:
                        await bot.send_message(config.CHAT_ID, f"🎉 <b>Телепатия сработала!</b> 🎉\nСлово: {word}\nОтветы: {ans_danila['raw']} / {ans_polina['raw']}!")
                    else:
                        await bot.send_message(config.CHAT_ID, f"❌ <b>Телепатия не сработала</b> ❌\nСлово: {word}\nДаня: {ans_danila['raw']}\nПолина: {ans_polina['raw']}")
                    await session.commit()
