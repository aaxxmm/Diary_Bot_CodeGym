import asyncio
import logging
import sys
import time
import os
import signal

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydub import AudioSegment
from aiogram.client.session.aiohttp import AiohttpSession

import subprocess

# for cmd in ["ffmpeg", "ffprobe"]:
#     try:
#         result = subprocess.run(
#             [cmd, "-version"],
#             capture_output=True,
#             text=True
#         )
#         print(f"{cmd} OK")
#         print(result.stdout[:200])
#     except Exception as e:
#         print(f"{cmd} ERROR:", e)

import shutil
ffmpeg_path = shutil.which('ffmpeg')
ffprobe_path = shutil.which('ffprobe')
print(f"ffmpeg: {'found' if ffmpeg_path else 'NOT found'}")
print(f"ffprobe: {'found' if ffprobe_path else 'NOT found'}")

print("========== ENV ==========")
print(os.environ)
print("=========================")
print("TOKEN_TG =", os.getenv("TOKEN_TG"))

import config
from handlers import all_routers
from scheduler.tasks import check_overdue_tasks, check_upcoming_deadlines, check_birthdays

# ДИАГНОСТИКА: покажет все переменные окружения (только для отладки!)
print("=" * 50)
print("ДОСТУПНЫЕ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ:")
print("=" * 50)
for key in os.environ.keys():
    if "TOKEN" in key or "TG" in key or "WEATHER" in key or "OPENAI" in key:
        print(f"  {key} = {os.environ[key][:20]}..." if len(os.environ.get(key, "")) > 20 else f"  {key} = {os.environ[key]}")
print("=" * 50)

# Проверяем конкретно TOKEN_TG
tg_token = os.getenv("TOKEN_TG")
print(f"🔍 TOKEN_TG = {tg_token[:20] if tg_token else 'НЕ НАЙДЕН'}...")
# ЗАДЕРЖКА ПРИ СТАРТЕ (важно для Amvera!)
# ============================================
time.sleep(7)

# ============================================
# ОТКЛЮЧЕНИЕ ПРОКСИ
# ============================================
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
              'ALL_PROXY', 'all_proxy', 'SOCKS_PROXY', 'socks_proxy',
              'socks4_proxy', 'socks5_proxy']
for var in proxy_vars:
    os.environ.pop(var, None)

os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# ============================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================
# Проверяем корректность уровня логирования
log_level_str = config.settings.log_level.upper()
if log_level_str not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    log_level_str = 'INFO'

    print("⚠️ Некорректный уровень логирования, используем INFO")

logging.basicConfig(
    level=getattr(logging, log_level_str),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Проверка ffmpeg при старте
def check_ffmpeg():
    import shutil
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    if ffmpeg_path:
        logger.info(f"✅ ffmpeg найден: {ffmpeg_path}")
    else:
        logger.warning("❌ ffmpeg НЕ НАЙДЕН! Голосовые сообщения не будут работать")

    if ffprobe_path:
        logger.info(f"✅ ffprobe найден: {ffprobe_path}")
    else:
        logger.warning("❌ ffprobe НЕ НАЙДЕН! Голосовые сообщения не будут работать")


# Вызвать после настройки логгера
check_ffmpeg()

# ============================================
# ФУНКЦИИ ЗАПУСКА/ОСТАНОВКИ
# ============================================
async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    commands = [
        BotCommand(command="start", description="🏠 Запустить бота"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="info", description="ℹ️ Информация о боте"),
        BotCommand(command="fox", description="🦊 Показать лису"),
        BotCommand(command="weather_help", description="🌤️ Прогноз погоды"),
        BotCommand(command="weather_location", description="📍 Погода по городу"),
        BotCommand(command="prof", description="💼 Выбрать профессию"),
        BotCommand(command="skills", description="📚 Навыки по профессиям"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Бот успешно запущен!")


async def on_shutdown(bot: Bot, scheduler: AsyncIOScheduler = None):
    """Действия при остановке бота"""
    logger.info("🛑 Остановка бота...")

    # Останавливаем планировщик
    if scheduler:
        try:
            scheduler.shutdown(wait=True)
            logger.info("⏸️ Планировщик задач остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке планировщика: {e}")

    # Закрываем сессию бота
    try:
        await bot.session.close()
        logger.info("🔌 Сессия бота закрыта")
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии: {e}")

    logger.info("❌ Бот остановлен")


# ============================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================
async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Запуск бота...")

    # Проверка токена
    if not config.settings.bot_token:
        logger.error("❌ TOKEN_TG не найден в конфигурации!")
        logger.info("Убедитесь, что переменная TOKEN_TG установлена в секретах Amvera или .env файле")
        return

    TOKEN_TG = config.settings.bot_token

    # Создаем сессию с правильными таймаутами
    session = AiohttpSession(
        timeout=60,  # Общий таймаут
        read_timeout=60,  # Таймаут на чтение
        connect_timeout=30  # Таймаут на подключение
    )

    # Создаем бота и диспетчер
    bot = Bot(token=TOKEN_TG, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Вызываем действия при запуске
    await on_startup(bot)

    # Подключаем все роутеры
    if all_routers:
        for router in all_routers:
            dp.include_router(router)
            router_name = getattr(router, 'name', 'unnamed')
            logger.info(f"✅ Подключен роутер: {router_name}")

            # Дополнительная диагностика для AI роутеров
            if 'ai' in router_name.lower() or 'gpt' in router_name.lower():
                logger.info(f"   🤖 AI роутер обнаружен: {router_name}")
    else:
        logger.warning("⚠️ Нет подключенных роутеров!")

    # ============================================
    # НАСТРОЙКА ПЛАНИРОВЩИКА ЗАДАЧ
    # ============================================
    scheduler = AsyncIOScheduler(timezone=config.settings.default_timezone)
    tasks_added = 0

    try:
        scheduler.add_job(
            check_overdue_tasks,
            'interval',
            hours=6,  # Увеличено с 1 часа для снижения нагрузки
            args=[bot],
            id='overdue_tasks',
            replace_existing=True
        )
        logger.info("✅ Добавлена задача: проверка просроченных задач (каждые 6 часов)")
        tasks_added += 1
    except Exception as e:
        logger.warning(f"⚠️ Не удалось добавить задачу overdue_tasks: {e}")

    try:
        scheduler.add_job(
            check_upcoming_deadlines,
            'interval',
            minutes=30,  # Увеличено с 15 минут
            args=[bot],
            id='upcoming_deadlines',
            replace_existing=True
        )
        logger.info("✅ Добавлена задача: проверка ближайших дедлайнов (каждые 30 минут)")
        tasks_added += 1
    except Exception as e:
        logger.warning(f"⚠️ Не удалось добавить задачу upcoming_deadlines: {e}")

    try:
        scheduler.add_job(
            check_birthdays,
            'interval',
            hours=12,  # Увеличено с 6 часов
            args=[bot],
            id='birthdays',
            replace_existing=True
        )
        logger.info("✅ Добавлена задача: проверка дней рождений (каждые 12 часов)")
        tasks_added += 1
    except Exception as e:
        logger.warning(f"⚠️ Не удалось добавить задачу birthdays: {e}")

    # Запускаем планировщик только если есть задачи
    if tasks_added > 0:
        scheduler.start()
        logger.info("⏰ Планировщик задач запущен")
    else:
        logger.warning("⚠️ Планировщик не запущен (нет активных задач)")

    # ============================================
    # НАСТРОЙКА ОБРАБОТКИ СИГНАЛОВ (для graceful shutdown)
    # ============================================
    stop_signal = asyncio.Event()

    def handle_shutdown_signal():
        logger.info("🛑 Получен сигнал остановки...")
        stop_signal.set()

    # Только для Unix-систем (не Windows)
    if sys.platform != 'win32':
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown_signal)
        loop.add_signal_handler(signal.SIGINT, handle_shutdown_signal)

    # ============================================
    # ЗАПУСК БОТА
    # ============================================
    try:
        logger.info("🔄 Бот начал прослушивание сообщений...")

        # Запускаем polling и ждем сигнал остановки
        polling_task = asyncio.create_task(dp.start_polling(bot))

        # Ждем либо завершения polling, либо сигнала остановки
        await asyncio.wait([polling_task, asyncio.create_task(stop_signal.wait())],
                           return_when=asyncio.FIRST_COMPLETED)

        # Отменяем polling_task если он еще не завершен
        if not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        logger.info("⏸️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при работе бота: {e}")
        raise
    finally:
        await on_shutdown(bot, scheduler)


# ============================================
# ТОЧКА ВХОДА
# ============================================
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот завершил работу")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
