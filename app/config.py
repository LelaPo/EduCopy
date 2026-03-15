"""
Загрузка конфигурации из .env
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def parse_user_ids(value: str) -> set[int]:
    """Парсит список user_id через запятую."""
    ids = set()
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def get_env(key: str, default: str | None = None, required: bool = True) -> str:
    """Получить переменную окружения с проверкой."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Переменная окружения {key} не задана!")
    return value or ""


@dataclass
class TelegramConfig:
    bot_token: str
    allowed_user_ids: set[int]

@dataclass
class AutheduConfig:
    bearer_token: str
    student_id: str
    profile_id: str
    profile_type: str
    x_mes_subsystem: str
    cookie: str


@dataclass
class Config:
    telegram: TelegramConfig
    authedu: AutheduConfig
    timezone: str
    proxy_url: str | None


def load_config() -> Config:
    """Загрузить всю конфигурацию."""
    # Получаем SOCKS5 прокси из .env (формат: socks5://user:pass@host:port или socks5://host:port)
    proxy_host = get_env("PROXY_HOST", "", required=False)
    proxy_port = get_env("PROXY_PORT", "", required=False)
    proxy_user = get_env("PROXY_USER", "", required=False)
    proxy_pass = get_env("PROXY_PASS", "", required=False)
    
    proxy_url = None
    if proxy_host and proxy_port:
        if proxy_user and proxy_pass:
            proxy_url = f"socks5://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        else:
            proxy_url = f"socks5://{proxy_host}:{proxy_port}"
    
    return Config(
        telegram=TelegramConfig(
            bot_token=get_env("TG_BOT_TOKEN"),
            allowed_user_ids=parse_user_ids(get_env("ALLOWED_USER_ID")),
        ),
        authedu=AutheduConfig(
            bearer_token=get_env("AUTHEDU_BEARER"),
            student_id=get_env("STUDENT_ID"),
            profile_id=get_env("PROFILE_ID"),
            profile_type=get_env("PROFILE_TYPE", "student"),
            x_mes_subsystem=get_env("X_MES_SUBSYSTEM", "familyweb"),
            cookie=get_env("AUTHEDU_COOKIE", "", required=False),
        ),
        timezone=get_env("TIMEZONE", "Europe/Moscow"),
        proxy_url=proxy_url,
    )
