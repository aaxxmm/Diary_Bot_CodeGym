import config
import io
import logging
from aiogram import Router, F
from aiogram.types import Message, Voice
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from pydub import AudioSegment
import speech_recognition as sr

from typing import cast
from states.user_states import TranslateState
from utils.translate_service import translate_text
from keyboards.keyboar import main_keyboard, back_keyboard

logger = logging.getLogger(__name__)
router = Router(name="translate")


@router.message(TranslateState.waiting_for_text, F.text)
async def translate_text_handler(message: Message, state: FSMContext):
    """Обработка текста для перевода"""
    text_to_translate = message.text

    # ДИАГНОСТИКА
    logger.info("=== ТЕСТ ПЕРЕВОДА ===")
    logger.info(f"Текст: {message.text[:50] if message.text else 'None'}...")

    # Проверяем импорт translate_text
    logger.info(f"translate_text импортирована: {translate_text}")

    await message.answer("🔄 Перевожу...")

    # Переводим с английского на русский
    text = cast(str, message.text)
    translated = await translate_text(text_to_translate, source_lang="auto", target_lang="ru") # type: ignor

    logger.info(f"Translation result: {translated[:100] if translated else 'None'}")

    if translated and not translated.startswith("❌"):
        await message.answer(
            f"📝 *Исходный текст:*\n{text_to_translate}\n\n"
            f"🌐 *Перевод:*\n{translated}",
            parse_mode="Markdown",
            reply_markup=main_keyboard
        )
    else:
        await message.answer(
            f"❌ Не удалось перевести текст.\n\n{translated if translated else 'Попробуйте позже.'}",
            reply_markup=main_keyboard
        )

    await state.clear()


@router.message(TranslateState.waiting_for_text, F.voice)
async def translate_voice_handler(message: Message, state: FSMContext):
    """Обработка голосового сообщения для перевода"""

    voice: Voice = message.voice

    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение для перевода...")

    try:
        # Скачиваем голосовое сообщение
        file = await message.bot.get_file(voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)

        # Конвертируем для распознавания
        import io
        from pydub import AudioSegment
        import speech_recognition as sr

        audio = AudioSegment.from_file(io.BytesIO(voice_bytes.read()), format="ogg")

        # Распознаем речь
        recognizer = sr.Recognizer()
        with io.BytesIO() as wav_io:
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            with sr.AudioFile(wav_io) as source:
                recognizer.adjust_for_ambient_noise(source)
                audio_data = recognizer.record(source)

                # Пробуем распознать русский или английский
                try:
                    text = recognizer.recognize_google(audio_data, language="ru-RU")
                    await processing_msg.edit_text(f"🎤 Распознано (русский): {text}")
                except:
                    try:
                        text = recognizer.recognize_google(audio_data, language="en-US")
                        await processing_msg.edit_text(f"🎤 Распознано (английский): {text}")
                    except:
                        await processing_msg.edit_text("❌ Не удалось распознать речь")
                        return

                # Переводим
                from utils.translate_service import translate_text
                translated = await translate_text(text, source_lang="auto", target_lang="ru")

                if translated and not translated.startswith("❌"):
                    await message.answer(
                        f"📝 *Исходный текст:*\n{text}\n\n"
                        f"🌐 *Перевод:*\n{translated}",
                        parse_mode="Markdown"
                    )
                else:
                    await message.answer(
                        f"❌ Не удалось перевести текст.\n\n{translated if translated else 'Попробуйте позже.'}"
                    )

    except Exception as e:
        logger.error(f"Ошибка в translate_voice_handler: {e}")
        await processing_msg.edit_text("❌ Ошибка обработки голосового сообщения")
    finally:
        await state.clear()


@router.message(Command("cancel"))
async def cancel_translate(message: Message, state: FSMContext):
    """Отмена перевода"""
    current_state = await state.get_state()
    if current_state == TranslateState.waiting_for_text:
        await state.clear()
        await message.answer(
            "❌ Перевод отменен.",
            reply_markup=main_keyboard
        )