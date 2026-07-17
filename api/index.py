import os
import json
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from api.config import config
from api.database.connection import engine, Base, SupabaseStorage
from api.middlewares.bonus import AutoBonusMiddleware

from api.handlers.menu import router as menu_router
from api.handlers.balance import router as balance_router
from api.handlers.associations import router as associations_router
from api.handlers.dilemmas import router as dilemmas_router
from api.handlers.dreams import router as dreams_router
from api.handlers.quotes import router as quotes_router
from api.handlers.care import router as care_router
from api.handlers.games import router as games_router

# Initialize Bot and Dispatcher
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=SupabaseStorage())

# Access Middleware
class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        user = data.get("event_from_user")
        if not user or user.id not in (config.DANILA_ID, config.POLINA_ID):
            return
        return await handler(event, data)

dp.update.middleware(AccessMiddleware())
dp.update.middleware(AutoBonusMiddleware())

# Include Routers
dp.include_router(care_router) # Moved up so it intercepts specific commands/text before generic ones
dp.include_router(menu_router)
dp.include_router(balance_router)
dp.include_router(dilemmas_router)
dp.include_router(dreams_router)
dp.include_router(quotes_router)
dp.include_router(games_router)
dp.include_router(associations_router) # should be last if it has generic F.text handler without state

# FastAPI Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Temporary: Clear old dilemmas to load new ones
        from sqlalchemy import text
        try:
            await conn.execute(text("DELETE FROM dilemmas"))
            await conn.commit()
        except:
            pass
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    update_data = await request.json()
    update = Update(**update_data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)

@app.get("/api/set_webhook")
async def set_webhook():
    await bot.set_webhook(config.WEBHOOK_URL)
    return {"status": "ok", "url": config.WEBHOOK_URL}

# --- Import and register Cron Routers ---
from api.utils.cron import router as cron_router
# we need to pass bot to cron handlers. FastAPI dependency injection or global bot?
# We can just import the global `bot` in cron.py or pass it via request state, 
# but it's simpler to let cron.py import bot from api.index, however that causes circular imports.
# So we'll put cron endpoints in index.py OR inject bot into app.state.
app.include_router(cron_router)
app.state.bot = bot
