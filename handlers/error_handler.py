import logging
from aiogram import Router, types
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)
router = Router(name="error_handler")


@router.errors()
async def error_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок"""
    logger.error(f"❌ Ошибка: {event.exception}")
    logger.error(f"   Обновление: {event.update}")

    # Пытаемся отправить сообщение пользователю
    try:
        if event.update.message:
            await event.update.message.answer(
                "❌ Произошла ошибка. Пожалуйста, попробуйте позже.\n"
                "Если ошибка повторяется, используйте /start для перезапуска."
            )
        elif event.update.callback_query:
            await event.update.callback_query.answer(
                "❌ Произошла ошибка",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

    # Не перевыбрасываем исключение, чтобы бот не падал
    return True