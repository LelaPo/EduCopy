"""
Точка входа — запуск бота.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_config
from app.services.authedu_client import AutheduClient
from app.services.storage import Storage
from app.handlers.homework import router as homework_router, setup_handlers
from app.handlers.admin import router as admin_router, setup_admin_handlers


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота."""
    logger.info("Загрузка конфигурации...")
    
    try:
        config = load_config()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # ID администратора (создателя)
    admin_id = 1034877346
    
    logger.info(f"Admin ID: {admin_id}")
    
    # Создаём хранилище
    storage = Storage(admin_id=admin_id)
    
    # Создаём клиент API
    client = AutheduClient(config.authedu)
    
    # Инициализируем обработчики
    setup_handlers(config, client, storage)
    setup_admin_handlers(storage)
    
    # Создаём бота и диспетчер
    bot = Bot(
        token=config.telegram.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    
    # Важно: admin_router должен быть первым
    dp.include_router(admin_router)
    dp.include_router(homework_router)
    
    logger.info("Бот запускается (long polling)...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Закрытие соединений...")
        await client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен (Ctrl+C)")
