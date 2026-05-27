import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем .env только для локальной разработки
if os.path.exists('.env'):
    load_dotenv()
    logger.info("📁 Загружена конфигурация из .env файла")
else:
    logger.info("☁️ Используются переменные окружения (режим Amvera)")

# ОБЯЗАТЕЛЬНЫЕ ТОКЕНЫ

token_telegram = os.getenv("TOKEN_TG") or os.getenv("token_telegram")

# Weather API Token (поддерживаем оба варианта)
token_weather = os.getenv("WEATHER_APP_TOKEN") or os.getenv("WEATHER_API_KEY")

# OpenAI Token (поддерживаем несколько вариантов)
token_openai = (
        os.getenv("TOKEN_OPENAI") or
        os.getenv("OPENAI_API_KEY") or
        os.getenv("token_openai")
)

# НАСТРОЙКИ

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Saint-Petersburg")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# OpenAI настройки
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))

# API для картинок
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# База данных
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "bot.db"))

# Курсы валют
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY", "")

# ПРОВЕРКИ

errors = []
warnings = []

if not token_telegram:
    errors.append("❌ TOKEN_TG не найден! Бот не сможет запуститься")

if not token_weather:
    warnings.append("⚠️ WEATHER_APP_TOKEN не найден. Функции погоды будут недоступны")

if not token_openai:
    warnings.append("⚠️ TOKEN_OPENAI не найден. AI-функции (GPT) будут недоступны")

# Выводим предупреждения
for warning in warnings:
    logger.warning(warning)

# Критические ошибки
if errors:
    for error in errors:
        logger.error(error)
    raise ValueError("Отсутствуют обязательные переменные окружения")

# Статус загрузки (без вывода самих ключей!)
logger.info(f"✅ Конфигурация загружена:")
logger.info(f"   - Telegram токен: {'✅ есть' if token_telegram else '❌ нет'}")
logger.info(f"   - Weather токен: {'✅ есть' if token_weather else '❌ нет'}")
logger.info(f"   - OpenAI токен: {'✅ есть' if token_openai else '❌ нет'}")
logger.info(f"   - Город по умолчанию: {DEFAULT_CITY}")
logger.info(f"   - Admin ID: {ADMIN_USER_ID}")


class Settings:
    """Контейнер настроек бота"""

    @property
    def bot_token(self) -> str:
        return token_telegram

    @property
    def admin_user_id(self) -> int:
        return ADMIN_USER_ID

    @property
    def db_path(self) -> Path:
        return DATABASE_PATH

    @property
    def default_timezone(self) -> str:
        return DEFAULT_TIMEZONE

    @property
    def log_level(self) -> str:
        return LOG_LEVEL

    @property
    def default_city(self) -> str:
        return DEFAULT_CITY

    @property
    def openai_api_key(self) -> str:
        return token_openai or ""

    @property
    def openai_model(self) -> str:
        return OPENAI_MODEL

    @property
    def max_tokens(self) -> int:
        return MAX_TOKENS

    @property
    def unsplash_access_key(self) -> str:
        return UNSPLASH_ACCESS_KEY

    @property
    def unsplash_secret_key(self) -> str:
        return UNSPLASH_SECRET_KEY

    @property
    def pexels_api_key(self) -> str:
        return PEXELS_API_KEY

    @property
    def weather_token(self) -> str:
        return token_weather

    @property
    def currency_api_key(self) -> str:
        return CURRENCY_API_KEY


# Глобальный экземпляр для импорта
settings = Settings()