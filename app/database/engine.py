"""
Движок базы данных и сессии.
"""
import logging
from pathlib import Path
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

logger = logging.getLogger(__name__)

# Путь к файлу БД (рядом с main.py)
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data.db"
DB_URL = f"sqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    """Базовый класс для моделей."""
    pass


_engine: Engine | None = None
_session_maker: sessionmaker[Session] | None = None


def get_session_maker() -> sessionmaker[Session]:
    """Получить session maker."""
    if _session_maker is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db()")
    return _session_maker


def init_db():
    """Инициализировать движок и создать таблицы."""
    global _engine, _session_maker
    
    logger.info(f"Инициализация БД: {DB_PATH}")
    
    _engine = create_engine(
        DB_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},  # Нужно для aiosqlite
    )
    
    _session_maker = sessionmaker(
        bind=_engine,
        class_=Session,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Создаём все таблицы
    Base.metadata.create_all(_engine)
    
    logger.info("Таблицы созданы")


def close_db():
    """Закрыть соединение с БД."""
    if _engine:
        _engine.dispose()
        logger.info("Соединение с БД закрыто")


def get_db() -> Session:
    """Получить сессию БД."""
    if _session_maker is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db()")
    return _session_maker()
