import io
import logging
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Router, F
from aiogram.types import Message, Voice, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import main_keyboard, back_keyboard
from keyboards.keyboar import get_notes_reply_keyboard, get_ai_menu, get_hr_menu
from utils.random_picture import fox
from config import settings
from states.user_states import GPTStates, TranslateState

logger = logging.getLogger(__name__)

router = Router()


def get_cancel_inline_keyboard():
    """Инлайн клавиатура для отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="menu:ai")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Обработка голосовых сообщений для перевода и AI помощника"""

    # Получаем текущее состояние
    current_state = await state.get_state()
    logger.info(f"Голосовое сообщение в состоянии: {current_state}")

    # Проверяем, в каком режиме находимся
    is_translate_mode = (current_state == TranslateState.waiting_for_text)
    is_ai_mode = (current_state == GPTStates.waiting_for_question)

    if not is_translate_mode and not is_ai_mode:
        await message.answer(
            "🎤 Голосовые сообщения принимаются только в режимах:\n"
            "• 🌐 Перевод текста\n"
            "• 🤖 AI Помощник (чат, редактирование, резюме)\n\n"
            "Сначала выберите нужную функцию в меню."
        )
        return

    voice: Voice = message.voice

    # Показываем, что обрабатываем
    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")

    try:
        # Скачиваем голосовое сообщение
        file = await message.bot.get_file(voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)

        # Конвертируем OGG в WAV
        audio = AudioSegment.from_file(io.BytesIO(voice_bytes.read()), format="ogg")

        # Распознаем речь
        recognizer = sr.Recognizer()

        # Сохраняем в WAV для распознавания
        with io.BytesIO() as wav_io:
            audio.export(wav_io, format="wav")
            wav_io.seek(0)

            with sr.AudioFile(wav_io) as source:
                # Настраиваем для лучшего распознавания
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)

                # Пробуем распознать русский язык
                try:
                    text = recognizer.recognize_google(audio_data, language="ru-RU")
                    await processing_msg.edit_text(f"🎤 Распознано: {text}")

                    # Отправляем в соответствующий обработчик
                    if is_translate_mode:
                        # Для переводчика
                        from handlers.translate import translate_text_handler
                        # Создаем фейковое сообщение с текстом
                        message.text = text
                        await translate_text_handler(message, state)
                    elif is_ai_mode:
                        # Для AI помощника
                        message.text = text
                        # Вызываем обработчик AI напрямую
                        from handlers.ai_assistant import process_ai_request
                        await process_ai_request(message, state)

                except sr.UnknownValueError:
                    await processing_msg.edit_text(
                        "❌ Не удалось распознать речь.\n\n"
                        "Попробуйте:\n"
                        "• Говорить четче\n"
                        "• Уменьшить фоновый шум\n"
                        "• Отправить текстовое сообщение"
                    )
                except sr.RequestError as e:
                    logger.error(f"Ошибка сервиса распознавания: {e}")
                    await processing_msg.edit_text(
                        "❌ Ошибка сервиса распознавания речи.\n"
                        "Пожалуйста, попробуйте позже или отправьте текст."
                    )

    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}")
        await processing_msg.edit_text(
            "❌ Не удалось обработать голосовое сообщение.\n\n"
            "Убедитесь, что:\n"
            "• Голосовое сообщение не повреждено\n"
            "• Длительность не превышает 60 секунд\n"
            "• Отправьте текст вместо голоса"
        )


@router.message(Command("check_ffmpeg"))
async def check_ffmpeg_command(message: Message):
    """Проверка наличия ffmpeg"""
    import shutil
    import subprocess

    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    result = "🔍 **Проверка ffmpeg:**\n\n"

    if ffmpeg_path:
        result += f"✅ ffmpeg: {ffmpeg_path}\n"
        try:
            proc = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            version = proc.stdout.split('\n')[0]
            result += f"   Версия: {version[:60]}...\n"
        except:
            pass
    else:
        result += "❌ ffmpeg НЕ УСТАНОВЛЕН\n"

    if ffprobe_path:
        result += f"✅ ffprobe: {ffprobe_path}\n"
    else:
        result += "❌ ffprobe НЕ УСТАНОВЛЕН\n"

    if not ffmpeg_path or not ffprobe_path:
        result += "\n⚠️ Голосовые сообщения НЕ будут работать!\n"
        result += "Обратитесь к администратору для установки ffmpeg."

    await message.answer(result)