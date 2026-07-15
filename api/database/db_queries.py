from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.database.models import User, GameState

async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, balance=0)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def update_balance(session: AsyncSession, telegram_id: int, delta: int) -> User:
    user = await get_or_create_user(session, telegram_id)
    user.balance += delta
    await session.commit()
    await session.refresh(user)
    return user

async def get_game_state(session: AsyncSession, game_id: str) -> GameState:
    res = await session.execute(select(GameState).where(GameState.id == game_id))
    state = res.scalar_one_or_none()
    if not state:
        state = GameState(id=game_id, is_active=False, data="{}")
        session.add(state)
        await session.commit()
        await session.refresh(state)
    return state
