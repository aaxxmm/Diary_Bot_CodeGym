import logging
from typing import Optional
from utils.gpt_service import gpt_service

logger = logging.getLogger(__name__)

# Простая реализация перевода через словарь (для демонстрации)


# Простой словарь для демонстрации
TRANSLATIONS = {
    "hi": "привет",
    "hello": "здравствуйте",
    "how are you": "как дела",
    "good morning": "доброе утро",
    "good night": "спокойной ночи",
    "thank you": "спасибо",
    "please": "пожалуйста",
    "yes": "да",
    "no": "нет",
    "i love you": "я люблю тебя",
}


async def translate_text(text: str, source_lang: str = "auto", target_lang: str = "ru") -> Optional[str]:
    """
    Перевод текста с использованием GPT
    """
    try:
        # Определяем язык для более точного перевода
        # Проверяем наличие кириллицы
        if any('\u0400' <= char <= '\u04FF' for char in text):
            source = "ru"
            target = "en"
        else:
            source = source_lang
            target = target_lang

        prompt = f"Переведи следующий текст с {source} на {target}. Переведи только текст, без пояснений и кавычек:\n\n{text}"

        logger.info(f"Sending translation request to GPT")
        translation = await gpt_service.get_response(
            prompt=prompt,
            max_tokens=500,
            temperature=0.3
        )

        # Очищаем ответ от лишних символов
        if translation:
            translation = translation.strip().strip('"').strip("'")
            logger.info(f"Translation received: {translation[:100]}...")

        return translation

    except Exception as e:
        logger.error(f"Translation error: {e}")
        return f"❌ Ошибка перевода: {str(e)}"