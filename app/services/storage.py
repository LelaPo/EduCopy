"""
Хранение данных в SQLite базе.
"""
import logging
import secrets
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, sessionmaker, joinedload

from app.database.models import User, AccessKey
from app.database.engine import get_session_maker

logger = logging.getLogger(__name__)


class Storage:
    """Менеджер хранения данных в SQLite."""

    def __init__(self, admin_id: int):
        self.admin_id = admin_id
        self._session_maker: sessionmaker[Session] | None = None

    def set_session_maker(self, session_maker: sessionmaker[Session]):
        """Установить session maker."""
        self._session_maker = session_maker

    def _get_session(self) -> Session:
        """Получить сессию."""
        if self._session_maker is None:
            raise RuntimeError("Session maker не установлен")
        return self._session_maker()

    def _ensure_admin(self):
        """Убедиться, что администратор существует в БД."""
        with self._get_session() as session:
            admin = session.get(User, self.admin_id)
            if admin is None:
                admin = User(
                    user_id=self.admin_id,
                    username="admin",
                    is_admin=True,
                    activated_at=datetime.utcnow(),
                )
                session.add(admin)
                session.commit()
                logger.info(f"Администратор {self.admin_id} добавлен в БД")

    def generate_key(self) -> str:
        """Создать новый уникальный ключ."""
        with self._get_session() as session:
            # Формат: XXXX-XXXX-XXXX (12 символов, буквы и цифры)
            chars = string.ascii_uppercase + string.digits

            while True:
                parts = [
                    ''.join(secrets.choice(chars) for _ in range(4))
                    for _ in range(3)
                ]
                key = '-'.join(parts)

                # Проверяем уникальность через select по полю key
                existing = session.execute(
                    select(AccessKey).where(AccessKey.key == key)
                ).scalar_one_or_none()
                if existing is None:
                    break

            # Сохраняем ключ
            access_key = AccessKey(
                key=key,
                created_at=datetime.utcnow(),
            )
            session.add(access_key)
            session.commit()

            # Проверяем что ключ сохранился через select по полю key
            saved_key = session.execute(
                select(AccessKey).where(AccessKey.key == key)
            ).scalar_one_or_none()
            if saved_key is None:
                logger.error(f"Ключ {key} не сохранился в БД!")
            else:
                logger.info(f"Ключ {key} успешно сохранён в БД (id={saved_key.id})")

            logger.info(f"Создан новый ключ: {key}")
            return key

    def get_all_keys(self) -> list[AccessKey]:
        """Получить все ключи."""
        with self._get_session() as session:
            result = session.execute(
                select(AccessKey)
                .options(joinedload(AccessKey.user))
                .order_by(AccessKey.is_used, AccessKey.created_at.desc())
            )
            return list(result.scalars().unique().all())

    def get_unused_keys(self) -> list[AccessKey]:
        """Получить неиспользованные ключи."""
        with self._get_session() as session:
            result = session.execute(
                select(AccessKey)
                .where(AccessKey.user_id.is_(None))
                .order_by(AccessKey.created_at.desc())
            )
            return list(result.scalars().all())

    def get_used_keys(self) -> list[AccessKey]:
        """Получить использованные ключи."""
        with self._get_session() as session:
            result = session.execute(
                select(AccessKey)
                .options(joinedload(AccessKey.user))
                .where(AccessKey.user_id.isnot(None))
                .order_by(AccessKey.created_at.desc())
            )
            return list(result.scalars().unique().all())

    def delete_key(self, key: str) -> bool:
        """Удалить ключ."""
        with self._get_session() as session:
            access_key = session.execute(
                select(AccessKey).where(AccessKey.key == key)
            ).scalar_one_or_none()
            if access_key is None:
                return False

            # Если ключ был активирован - удаляем и пользователя
            if access_key.user_id:
                user = session.get(User, access_key.user_id)
                if user:
                    session.delete(user)

            session.delete(access_key)
            session.commit()

            logger.info(f"Удалён ключ: {key}")
            return True

    def activate_key(self, key: str, user_id: int, username: str | None) -> bool:
        """Активировать ключ для пользователя."""
        with self._get_session() as session:
            logger.info(f"Попытка активации ключа {key} для пользователя {user_id}")

            # Проверяем что ключ существует и не использован через select по полю key
            access_key = session.execute(
                select(AccessKey).where(AccessKey.key == key)
            ).scalar_one_or_none()
            if access_key is None:
                logger.warning(f"Ключ {key} не найден в БД")
                return False

            if access_key.user_id is not None:
                logger.warning(f"Ключ {key} уже активирован пользователем {access_key.user_id}")
                return False

            # Проверяем что пользователь ещё не активировал ключ
            existing_user = session.get(User, user_id)
            if existing_user is not None:
                logger.warning(f"Пользователь {user_id} уже активирован")
                return False

            # Активируем ключ
            now = datetime.utcnow()
            access_key.user_id = user_id

            # Создаём пользователя
            user = User(
                user_id=user_id,
                username=username,
                activated_at=now,
                is_admin=False,
            )
            session.add(user)
            session.commit()

            logger.info(f"Ключ {key} активирован пользователем {user_id} ({username})")
            return True

    def is_authorized(self, user_id: int) -> bool:
        """Проверить авторизован ли пользователь."""
        # Админ всегда авторизован
        if user_id == self.admin_id:
            self._ensure_admin()
            return True
        
        with self._get_session() as session:
            user = session.get(User, user_id)
            return user is not None

    def is_admin(self, user_id: int) -> bool:
        """Проверить является ли пользователь админом."""
        return user_id == self.admin_id

    def get_user_count(self) -> int:
        """Количество авторизованных пользователей."""
        with self._get_session() as session:
            result = session.execute(
                select(func.count(User.user_id))
            )
            return result.scalar() or 0

    def get_all_users(self) -> list[User]:
        """Получить всех пользователей."""
        with self._get_session() as session:
            result = session.execute(
                select(User).order_by(User.activated_at.desc())
            )
            return list(result.scalars().all())

    def revoke_access(self, user_id: int) -> bool:
        """Отозвать доступ у пользователя."""
        with self._get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                return False

            # Освобождаем ключ
            if user.key_id:
                access_key = session.get(AccessKey, user.key_id)
                if access_key:
                    access_key.user_id = None

            session.delete(user)
            session.commit()

            logger.info(f"Пользователь {user_id} удалён, ключ освобождён")
            return True
