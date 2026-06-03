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

from pydub import AudioSegment
import shutil

# Явно указываем пути к ffmpeg и ffprobe
ffmpeg_path = shutil.which('ffmpeg')
ffprobe_path = shutil.which('ffprobe')

if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path
    print(f"✅ ffmpeg установлен: {ffmpeg_path}")

if ffprobe_path:
    AudioSegment.ffprobe = ffprobe_path
    print(f"✅ ffprobe установлен: {ffprobe_path}")

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


@router.message(F.voice)
async def test_voice_handler(message: Message, state: FSMContext):
    """Тестовый обработчик голоса"""
    logger.info("=" * 50)
    logger.info("🎤 ПОЛУЧЕНО ГОЛОСОВОЕ СООБЩЕНИЕ")
    logger.info(f"User: {message.from_user.id}")
    logger.info(f"State: {await state.get_state()}")
    logger.info("=" * 50)

    await message.answer(
        "🎤 Голосовое сообщение получено!\n\n"
        f"Текущий режим: {await state.get_state() or 'не выбран'}\n\n"
        "Выберите режим:\n"
        "• 🌐 Переводчик\n"
        "• 🤖 AI Помощник"
    )


@router.callback_query(F.data == "menu:main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        "🏠 *Главное меню*\n\n"
        "Выберите нужную функцию:",
        parse_mode="Markdown"
    )

    # Отправляем новое сообщение с клавиатурой
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "menu:ai")
async def show_ai_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню AI помощника"""
    await state.clear()

    await callback.message.edit_text(
        "🤖 *AI Помощник*\n\n"
        "Выберите нужную функцию:\n\n"
        "• 🌐 *Перевод текста* - перевод на любой язык\n"
        "• ✍️ *Редактирование* - исправление ошибок, улучшение стиля\n"
        "• 📝 *Резюме* - краткое изложение текста\n\n"
        "Все функции используют искусственный интеллект GPT.",
        parse_mode="Markdown",
        reply_markup=get_ai_menu().as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:gpt")
async def show_gpt_chat(callback: CallbackQuery, state: FSMContext):
    """Показать чат с GPT"""
    from states.user_states import GPTStates

    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(ai_mode="chat")

    await callback.message.edit_text(
        "🤖 *Чат с ChatGPT*\n\n"
        "Задайте мне любой вопрос, и я постараюсь на него ответить!\n\n"
        "Я могу помочь с:\n"
        "• Ответами на вопросы\n"
        "• Советами и рекомендациями\n"
        "• Объяснением сложных тем\n"
        "• Переводом текста\n\n"
        "Просто напишите ваш вопрос ниже:",
        parse_mode="Markdown",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "ai:translate")
async def ai_translate_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки перевода в AI меню"""
    from states.user_states import TranslateState

    await state.set_state(TranslateState.waiting_for_text)

    await callback.message.edit_text(
        "🌐 *AI Перевод текста*\n\n"
        "Отправьте текст для перевода.\n\n"
        "Я переведу его с любого языка на русский (или наоборот).\n\n"
        "Примеры:\n"
        "• 'Hello, how are you?'\n"
        "• 'Привет, как дела?'\n"
        "• Отправьте голосовое сообщение",
        parse_mode="Markdown",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "ai:edit")
async def ai_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки редактирования текста в AI меню"""
    from states.user_states import GPTStates

    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(edit_mode=True, ai_mode="edit")

    await callback.message.edit_text(
        "✍️ *AI Редактирование текста*\n\n"
        "Отправьте текст, который нужно отредактировать.\n\n"
        "Я могу:\n"
        "• Исправить грамматические ошибки\n"
        "• Улучшить стиль текста\n"
        "• Сделать текст более профессиональным\n\n"
        "Просто напишите текст:",
        parse_mode="Markdown",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "ai:summarize")
async def ai_summarize_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки резюме заметок в AI меню"""
    from states.user_states import GPTStates

    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(summarize_mode=True, ai_mode="summarize")

    await callback.message.edit_text(
        "📝 *AI Резюме текста*\n\n"
        "Отправьте текст, который нужно сократить или сделать краткое резюме.\n\n"
        "Я сделаю:\n"
        "• Краткое изложение основного содержания\n"
        "• Выделю ключевые моменты\n"
        "• Сохраню важную информацию\n\n"
        "Отправьте текст для анализа:",
        parse_mode="Markdown",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.\n\n"
        "Вернуться в главное меню: /start",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    """Обработка неизвестных callback-запросов"""
    logger.warning(f"Неизвестный callback: {callback.data}")
    await callback.answer("❌ Неизвестная команда", show_alert=False)


@router.message(F.text == "🤖 AI Помощник")
async def ai_menu_text_button(message: Message, state: FSMContext):
    """Обработка кнопки AI Помощник"""
    await state.clear()
    await message.answer(
        "🤖 *AI Помощник*\n\n"
        "Выберите нужную функцию:",
        parse_mode="Markdown",
        reply_markup=get_ai_menu().as_markup()
    )


@router.message(F.text == "🌐 Переводчик")
async def translate_text_button(message: Message, state: FSMContext):
    """Обработка кнопки Переводчик"""
    from states.user_states import TranslateState

    await state.set_state(TranslateState.waiting_for_text)
    await message.answer(
        "🌐 Отправьте текст для перевода:\n\n"
        "Пример: 'Hello, how are you?'",
        reply_markup=back_keyboard
    )