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

from pydub import AudioSegment
import shutil

# Явно указываем пути к ffmpeg и ffprobe
ffmpeg_path = shutil.which('ffmpeg')
ffprobe_path = shutil.which('ffprobe')

if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path

if ffprobe_path:
    AudioSegment.ffprobe = ffprobe_path

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
    """Обработка голосового сообщения через Whisper"""
    # Просто перенаправляем в общий обработчик
    from handlers.common import handle_voice_whisper
    await handle_voice_whisper(message, state)


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