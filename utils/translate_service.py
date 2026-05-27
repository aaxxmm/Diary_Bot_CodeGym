import logging
from typing import Optional
from utils.gpt_service import gpt_service

logger = logging.getLogger(__name__)


async def translate_text(text: str, source_lang: str = "auto", target_lang: str = "ru") -> Optional[str]:
    """
    Перевод текста с использованием GPT
    """
    if not text or len(text.strip()) == 0:
        return "❌ Нет текста для перевода."

    try:
        # Определяем язык по наличию кириллицы
        has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)

        if has_cyrillic:
            source = "ru"
            target = "en" if target_lang == "ru" else target_lang
        else:
            source = source_lang if source_lang != "auto" else "en"
            target = target_lang

        prompt = f"Переведи следующий текст с {source} на {target}. Переведи только текст, без пояснений и кавычек:\n\n{text}"

        logger.info(f"Translation request: {text[:50]}... ({source} -> {target})")

        translation = await gpt_service.get_response(
            prompt=prompt,
            max_tokens=500,
            temperature=0.3
        )

        if translation:
            # Очищаем ответ от лишних символов
            translation = translation.strip().strip('"').strip("'")
            logger.info(f"Translation result: {translation[:100]}...")
            return translation
        else:
            return "❌ Не удалось перевести текст. Попробуйте позже."

    except Exception as e:
        logger.error(f"Translation error: {e}")
        return f"❌ Ошибка перевода: {str(e)}"
