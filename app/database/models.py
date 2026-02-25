"""
Модели базы данных.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.engine import Base


class AccessKey(Base):
    """Ключ доступа."""

    __tablename__ = "access_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь с пользователем (один ключ — один пользователь)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Обратная связь с пользователем
    user: Mapped[Optional["User"]] = relationship(
        "User",
        uselist=False,
        foreign_keys=[user_id],
    )

    @property
    def is_used(self) -> bool:
        return self.user_id is not None

    def __repr__(self) -> str:
        return f"<AccessKey {self.key}>"


class User(Base):
    """Авторизованный пользователь."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связь с ключом
    key_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("access_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    key: Mapped[Optional["AccessKey"]] = relationship(
        "AccessKey",
        uselist=False,
        foreign_keys=[key_id],
    )

    def __repr__(self) -> str:
        return f"<User {self.user_id} ({self.username})>"
