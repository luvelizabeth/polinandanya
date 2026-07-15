import json
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from aiogram.fsm.storage.base import BaseStorage, StorageKey

from api.config import config
from api.database.models import FSMData, Base

engine = create_async_engine(config.DB_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def make_key(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"

class SupabaseStorage(BaseStorage):
    async def set_state(self, key: StorageKey, state: str = None) -> None:
        k = make_key(key)
        async with async_session() as session:
            res = await session.execute(select(FSMData).where(FSMData.key == k))
            obj = res.scalar_one_or_none()
            if not obj:
                obj = FSMData(key=k, state=state.state if state else None)
                session.add(obj)
            else:
                obj.state = state.state if state else None
            await session.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        k = make_key(key)
        async with async_session() as session:
            res = await session.execute(select(FSMData).where(FSMData.key == k))
            obj = res.scalar_one_or_none()
            return obj.state if obj else None

    async def set_data(self, key: StorageKey, data: dict) -> None:
        k = make_key(key)
        async with async_session() as session:
            res = await session.execute(select(FSMData).where(FSMData.key == k))
            obj = res.scalar_one_or_none()
            if not obj:
                obj = FSMData(key=k, data=json.dumps(data))
                session.add(obj)
            else:
                obj.data = json.dumps(data)
            await session.commit()

    async def get_data(self, key: StorageKey) -> dict:
        k = make_key(key)
        async with async_session() as session:
            res = await session.execute(select(FSMData).where(FSMData.key == k))
            obj = res.scalar_one_or_none()
            return json.loads(obj.data) if obj and obj.data else {}

    async def close(self) -> None: pass
