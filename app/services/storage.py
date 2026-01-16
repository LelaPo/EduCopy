"""
Хранение данных: ключи доступа и пользователи.
Данные сохраняются в JSON файл.
"""
import json
import logging
import secrets
import string
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# Путь к файлу с данными (рядом с main.py)
DATA_FILE = Path(__file__).parent.parent.parent / "data.json"


@dataclass
class AccessKey:
    """Ключ доступа."""
    key: str
    created_at: str
    activated_by: Optional[int] = None
    activated_by_username: Optional[str] = None
    activated_at: Optional[str] = None
    
    @property
    def is_used(self) -> bool:
        return self.activated_by is not None


@dataclass  
class User:
    """Авторизованный пользователь."""
    user_id: int
    username: Optional[str]
    key_used: str
    activated_at: str


class Storage:
    """Менеджер хранения данных."""
    
    def __init__(self, admin_id: int):
        self.admin_id = admin_id
        self._data: dict = {"keys": {}, "users": {}}
        self._load()
    
    def _load(self):
        """Загрузить данные из файла."""
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(f"Загружено данных: {len(self._data.get('keys', {}))} ключей, {len(self._data.get('users', {}))} пользователей")
            except Exception as e:
                logger.error(f"Ошибка загрузки данных: {e}")
                self._data = {"keys": {}, "users": {}}
        else:
            self._data = {"keys": {}, "users": {}}
    
    def _save(self):
        """Сохранить данные в файл."""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def generate_key(self) -> str:
        """Создать новый уникальный ключ."""
        # Формат: XXXX-XXXX-XXXX (12 символов, буквы и цифры)
        chars = string.ascii_uppercase + string.digits
        while True:
            parts = [
                ''.join(secrets.choice(chars) for _ in range(4))
                for _ in range(3)
            ]
            key = '-'.join(parts)
            if key not in self._data["keys"]:
                break
        
        # Сохраняем ключ
        self._data["keys"][key] = {
            "created_at": datetime.now().isoformat(),
            "activated_by": None,
            "activated_by_username": None,
            "activated_at": None,
        }
        self._save()
        logger.info(f"Создан новый ключ: {key}")
        return key
    
    def get_all_keys(self) -> list[AccessKey]:
        """Получить все ключи."""
        keys = []
        for key, data in self._data.get("keys", {}).items():
            keys.append(AccessKey(
                key=key,
                created_at=data.get("created_at", ""),
                activated_by=data.get("activated_by"),
                activated_by_username=data.get("activated_by_username"),
                activated_at=data.get("activated_at"),
            ))
        # Сортируем: сначала неиспользованные, потом по дате
        keys.sort(key=lambda x: (x.is_used, x.created_at), reverse=True)
        return keys
    
    def get_unused_keys(self) -> list[AccessKey]:
        """Получить неиспользованные ключи."""
        return [k for k in self.get_all_keys() if not k.is_used]
    
    def get_used_keys(self) -> list[AccessKey]:
        """Получить использованные ключи."""
        return [k for k in self.get_all_keys() if k.is_used]
    
    def delete_key(self, key: str) -> bool:
        """Удалить ключ."""
        if key in self._data["keys"]:
            # Если ключ был активирован - удаляем и пользователя
            key_data = self._data["keys"][key]
            if key_data.get("activated_by"):
                user_id = str(key_data["activated_by"])
                if user_id in self._data.get("users", {}):
                    del self._data["users"][user_id]
            
            del self._data["keys"][key]
            self._save()
            logger.info(f"Удалён ключ: {key}")
            return True
        return False
    
    def activate_key(self, key: str, user_id: int, username: str | None) -> bool:
        """Активировать ключ для пользователя."""
        # Проверяем что ключ существует и не использован
        if key not in self._data["keys"]:
            return False
        
        key_data = self._data["keys"][key]
        if key_data.get("activated_by") is not None:
            return False
        
        # Проверяем что пользователь ещё не активировал ключ
        if str(user_id) in self._data.get("users", {}):
            return False
        
        # Активируем
        now = datetime.now().isoformat()
        self._data["keys"][key]["activated_by"] = user_id
        self._data["keys"][key]["activated_by_username"] = username
        self._data["keys"][key]["activated_at"] = now
        
        if "users" not in self._data:
            self._data["users"] = {}
        
        self._data["users"][str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "key_used": key,
            "activated_at": now,
        }
        
        self._save()
        logger.info(f"Ключ {key} активирован пользователем {user_id} ({username})")
        return True
    
    def is_authorized(self, user_id: int) -> bool:
        """Проверить авторизован ли пользователь."""
        # Админ всегда авторизован
        if user_id == self.admin_id:
            return True
        return str(user_id) in self._data.get("users", {})
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить является ли пользователь админом."""
        return user_id == self.admin_id
    
    def get_user_count(self) -> int:
        """Количество авторизованных пользователей."""
        return len(self._data.get("users", {}))
