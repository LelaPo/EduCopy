"""
HTTP-клиент для API authedu.mosreg.ru
"""
import httpx
import asyncio
import logging
from datetime import date
from dataclasses import dataclass, field
from app.config import AutheduConfig

logger = logging.getLogger(__name__)

# Новый API endpoint - только ДЗ
BASE_URL = "https://authedu.mosreg.ru/api/family/web/v1/homeworks"


@dataclass
class MaterialItem:
    """Один материал/файл."""
    title: str
    url: str


@dataclass
class HomeworkItem:
    """Одно домашнее задание."""
    subject: str
    homework_date: date
    homework_text: str
    is_done: bool
    materials: list[MaterialItem] = field(default_factory=list)


class AutheduAPIError(Exception):
    """Ошибка API автодневника."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AutheduClient:
    """Асинхронный клиент для получения ДЗ."""
    
    def __init__(self, config: AutheduConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
    
    def _get_headers(self) -> dict[str, str]:
        """Сформировать заголовки запроса."""
        headers = {
            "Authorization": f"Bearer {self.config.bearer_token}",
            "Profile-Id": self.config.profile_id,
            "Profile-Type": self.config.profile_type,
            "X-mes-subsystem": self.config.x_mes_subsystem,
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        if self.config.cookie:
            headers["Cookie"] = self.config.cookie
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP-клиент."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers=self._get_headers(),
            )
        return self._client
    
    async def close(self):
        """Закрыть HTTP-клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def fetch_homeworks(
        self, 
        from_date: date, 
        to_date: date,
        max_retries: int = 3,
    ) -> list[HomeworkItem]:
        """
        Получить домашние задания за период.
        
        Args:
            from_date: начальная дата
            to_date: конечная дата
            max_retries: количество попыток при ошибках сети
            
        Returns:
            Список HomeworkItem
            
        Raises:
            AutheduAPIError: при ошибках API
        """
        params = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "student_id": self.config.student_id,
        }
        
        client = await self._get_client()
        last_error: Exception | None = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Запрос ДЗ: {from_date} - {to_date} (попытка {attempt + 1})")
                response = await client.get(BASE_URL, params=params)
                
                if response.status_code == 401:
                    raise AutheduAPIError(
                        "❌ Токен авторизации истёк или неверен (401).\n"
                        "Обнови AUTHEDU_BEARER в .env",
                        status_code=401,
                    )
                
                if response.status_code == 403:
                    raise AutheduAPIError(
                        "❌ Доступ запрещён (403). Проверь Profile-Id и STUDENT_ID.",
                        status_code=403,
                    )
                
                if response.status_code >= 400:
                    raise AutheduAPIError(
                        f"❌ Ошибка API: HTTP {response.status_code}",
                        status_code=response.status_code,
                    )
                
                data = response.json()
                return self._parse_homeworks(data)
                
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Таймаут запроса (попытка {attempt + 1})")
                
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Ошибка сети: {e} (попытка {attempt + 1})")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Ожидание {wait_time} сек перед повтором...")
                await asyncio.sleep(wait_time)
        
        raise AutheduAPIError(
            f"❌ Не удалось подключиться к API после {max_retries} попыток.\n"
            f"Последняя ошибка: {last_error}"
        )
    
    def _parse_homeworks(self, data) -> list[HomeworkItem]:
        """Парсинг ответа API в список HomeworkItem."""
        items: list[HomeworkItem] = []
        
        # API может вернуть разные структуры
        if isinstance(data, dict):
            # Если словарь - ищем массив внутри
            data = data.get("payload") or data.get("response") or data.get("data") or []
        
        if not isinstance(data, list):
            logger.warning(f"Неожиданный формат данных: {type(data)}")
            return items
        
        for hw in data:
            # Пропускаем если это не словарь
            if not isinstance(hw, dict):
                logger.warning(f"Пропускаем элемент: {type(hw)}")
                continue
            
            # Текст ДЗ
            homework_text = hw.get("homework") or hw.get("description") or ""
            homework_text = str(homework_text).strip()
            
            # Пропускаем если нет текста ДЗ
            if not homework_text:
                continue
            
            # Дата
            date_str = hw.get("date", "")
            try:
                homework_date = date.fromisoformat(date_str)
            except ValueError:
                continue
            
            # Предмет
            subject = hw.get("subject_name", "Без предмета")
            
            # Статус выполнения
            is_done = hw.get("is_done", False)
            
            # Материалы
            materials: list[MaterialItem] = []
            materials_raw = hw.get("materials") or []
            
            for mat in materials_raw:
                if not isinstance(mat, dict):
                    continue
                
                title = mat.get("title", "Файл")
                urls = mat.get("urls") or []
                
                for url_obj in urls:
                    if isinstance(url_obj, dict) and url_obj.get("url"):
                        materials.append(MaterialItem(
                            title=title,
                            url=url_obj["url"],
                        ))
                        break
            
            items.append(HomeworkItem(
                subject=subject,
                homework_date=homework_date,
                homework_text=homework_text,
                is_done=is_done,
                materials=materials,
            ))
        
        items.sort(key=lambda x: (x.homework_date, x.subject))
        return items
