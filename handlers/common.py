import io
import logging
from aiogram import Router, F
from aiogram.types import Message, Voice, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI

from keyboards import main_keyboard, back_keyboard
from keyboards.keyboar import get_notes_reply_keyboard, get_ai_menu, get_hr_menu
from utils import gpt_service
from utils.random_picture import fox
from config import settings
from states.user_states import GPTStates, TranslateState

logger = logging.getLogger(__name__)
router = Router()

# Инициализация OpenAI клиента для Whisper
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


@router.message(F.voice)
async def handle_voice_whisper(message: Message, state: FSMContext):
    """Обработка голосовых сообщений через Whisper API"""

    current_state = await state.get_state()
    is_translate_mode = (current_state == TranslateState.waiting_for_text)
    is_ai_mode = (current_state == GPTStates.waiting_for_question)

    if not is_translate_mode and not is_ai_mode:
        await message.answer(
            "🎤 Сначала выберите режим:\n"
            "• 🌐 Переводчик\n"
            "• 🤖 AI Помощник"
        )
        return

    processing_msg = await message.answer("🎤 Распознаю голосовое сообщение через Whisper...")

    try:
        # Скачиваем голосовое сообщение
        file = await message.bot.get_file(message.voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)

        # Отправляем в Whisper API
        audio_file = io.BytesIO(voice_bytes.read())
        audio_file.name = "voice.ogg"

        # Используем OpenAI Whisper для распознавания
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru",
            response_format="text"
        )

        recognized_text = transcript if isinstance(transcript, str) else transcript.text

        await processing_msg.edit_text(f"🎤 Распознано: {recognized_text}")

        # Обработка в зависимости от режима
        if is_translate_mode:
            # Переводим через GPT
            prompt = f"Переведи следующий текст на русский язык (если текст не на русском) или исправь ошибки (если на русском):\n\n{recognized_text}"
            translation = await gpt_service.get_response(prompt, max_tokens=500, temperature=0.3)

            if translation and not translation.startswith("❌"):
                await message.answer(
                    f"📝 *Исходный текст:*\n{recognized_text}\n\n"
                    f"🌐 *Результат:*\n{translation}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(f"❌ Не удалось обработать текст.\n\n{translation}")

        elif is_ai_mode:
            data = await state.get_data()
            edit_mode = data.get("edit_mode", False)
            summarize_mode = data.get("summarize_mode", False)

            if edit_mode:
                prompt = f"Отредактируй следующий текст: исправь ошибки, сделай более понятным:\n\n{recognized_text}"
                response_prefix = "✍️ Отредактированный текст:\n\n"
            elif summarize_mode:
                prompt = f"Сделай краткое резюме текста:\n\n{recognized_text}"
                response_prefix = "📝 Резюме:\n\n"
            else:
                prompt = recognized_text
                response_prefix = "🤖 Ответ:\n\n"

            response = await gpt_service.get_response(prompt, max_tokens=1000, temperature=0.7)

            if response and not response.startswith("❌"):
                await message.answer(f"{response_prefix}{response}", parse_mode="Markdown")
            else:
                await message.answer(f"❌ Ошибка: {response}")

        await state.clear()

    except Exception as e:
        logger.error(f"Whisper ошибка: {e}")
        await processing_msg.edit_text(
            "❌ Не удалось распознать голосовое сообщение.\n\n"
            "Попробуйте:\n"
            "• Говорить четче\n"
            "• Отправить текстовое сообщение"
        )


def get_cancel_inline_keyboard():
    """Инлайн клавиатура для отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="menu:ai")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


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

@router.message(F.text == "🦊 Показать лису")
async def show_fox_button(message: Message):
    """Показать лису"""
    image_fox = await fox()
    if image_fox:
        await message.answer_photo(image_fox)
        await message.answer("🦊 Вот вам лиса! Понравилось?")
    else:
        await message.answer("❌ Не удалось получить фото лисы. Попробуйте позже.")


@router.message(F.text == "🌤️ Погода")
async def weather_menu_button(message: Message, state: FSMContext):
    """Показать меню погоды"""
    from keyboards.menu import get_weather_menu
    await state.clear()
    await message.answer(
        "🌤️ Выберите действие:",
        reply_markup=get_weather_menu().as_markup()
    )


@router.message(F.text == "📋 Задачи")
async def tasks_menu_button(message: Message, state: FSMContext):
    """Показать меню задач"""
    from keyboards.menu import get_tasks_menu
    await state.clear()
    await message.answer(
        "📋 Управление задачами:",
        reply_markup=get_tasks_menu().as_markup()
    )


@router.message(F.text == "🎂 Дни рождения")
async def birthdays_menu_button(message: Message, state: FSMContext):
    """Показать меню дней рождений"""
    from keyboards.menu import get_birthdays_menu
    await state.clear()
    await message.answer(
        "🎂 Управление днями рождения:",
        reply_markup=get_birthdays_menu().as_markup()
    )


@router.message(F.text == "📝 Заметки")
async def notes_menu_button(message: Message, state: FSMContext):
    """Показать меню заметок"""
    await state.clear()
    await message.answer(
        "📝 *Управление заметками*\n\n"
        "Здесь вы можете создавать, просматривать и управлять своими заметками.",
        reply_markup=get_notes_reply_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "💼 HR Рекрутер")
async def hr_menu_button(message: Message, state: FSMContext):
    """Показать меню HR рекрутера"""
    await state.clear()
    await message.answer(
        "💼 **HR Рекрутер помощник**\n\n"
        "Я помогу вам с выбором карьеры и развитием навыков!\n\n"
        "Доступные команды:\n"
        "• /prof - выбрать профессию\n"
        "• /skills - оценить навыки\n"
        "• /recommend - получить рекомендации",
        reply_markup=get_hr_menu().as_markup(),
        parse_mode="Markdown"
    )


@router.message(F.text == "ℹ️ Информация")
async def info_button(message: Message):
    """Показать информацию о боте"""
    await message.answer(
        '🤖 *Информация о боте*\n\n'
        'Это бот с подключением ChatGPT и функциями:\n'
        '• 🦊 Случайные фото лис\n'
        '• 🌤️ Прогноз погоды\n'
        '• 💬 Общение с ChatGPT\n'
        '• 📋 Управление задачами\n'
        '• 🎂 Дни рождения\n'
        '• 📝 Заметки\n'
        '• 💼 HR Рекрутер\n'
        '• 🌐 Переводчик',
        parse_mode="Markdown"
    )


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message):
    """Показать помощь"""
    help_text = (
        "📋 *Доступные команды:*\n\n"
        "/start - Начать работу\n"
        "/help - Показать эту справку\n"
        "/info - Информация о боте\n"
        "/fox - Случайное фото лисы\n\n"
        "🌤️ **Для погоды:**\n"
        "• Просто напишите название любого города\n\n"
        "📋 **Для задач:**\n"
        "• Используйте кнопки в меню задач\n\n"
        "🎂 **Для дней рождений:**\n"
        "• Используйте кнопки в меню дней рождений\n\n"
        "🤖 **Для AI помощника:**\n"
        "• Используйте кнопку 'AI Помощник' в главном меню"
    )
    await message.answer(help_text, parse_mode="Markdown")