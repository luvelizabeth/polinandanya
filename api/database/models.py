from datetime import date, datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, Date, Boolean, DateTime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    balance = Column(Integer, default=0)
    last_bonus_date = Column(Date, nullable=True)

class AssociationWord(Base):
    __tablename__ = 'association_words'
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False)
    is_used = Column(Boolean, default=False)

class Dilemma(Base):
    __tablename__ = 'dilemmas'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String, nullable=False)
    option1 = Column(String, nullable=False)
    option2 = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)

class Dream(Base):
    __tablename__ = 'dreams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    date = Column(Date, default=date.today)
    content = Column(String, nullable=False)
    is_voice = Column(Boolean, default=False)

class Quote(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=False)
    author_name = Column(String, nullable=False)
    added_by_id = Column(BigInteger, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

class GameState(Base):
    __tablename__ = 'game_states'
    id = Column(String, primary_key=True)
    is_active = Column(Boolean, default=False)
    data = Column(String, nullable=True)

class FSMData(Base):
    __tablename__ = 'fsm_data'
    key = Column(String, primary_key=True)
    state = Column(String, nullable=True)
    data = Column(String, default="{}")

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(BigInteger, nullable=False)
    receiver_id = Column(BigInteger, nullable=False)
    text = Column(String, nullable=False)
    send_at = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
