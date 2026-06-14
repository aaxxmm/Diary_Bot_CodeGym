# обрабатывает основное меню

import io
import logging
from aiogram import Router, F
from aiogram.types import Message, Voice, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI

from keyboards import main_keyboard, back_keyboard
from utils import gpt_service
from utils.random_picture import fox
from config import settings
from states.user_states import GPTStates, TranslateState
from keyboards.keyboar import get_ai_menu, get_hr_menu, get_notes_reply_keyboard, get_cancel_inline_keyboard


logger = logging.getLogger(__name__)
router = Router()

# Инициализация OpenAI клиента для Whisper
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


# ============= КОМАНДА START (ДОБАВИТЬ СЮДА) =============
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    # Получаем имя пользователя
    user_name = message.from_user.first_name
    if message.from_user.last_name:
        user_name = f"{message.from_user.first_name} {message.from_user.last_name}"

    # Сохраняем данные пользователя в состояние
    await state.update_data(
        user_name=user_name,
        user_id=message.from_user.id,
        username=message.from_user.username
    )

    # Приветственное сообщение с именем
    welcome_text = (
        f"👋 *Добро пожаловать, {user_name}!*\n\n"
        f"Я помогу вам с:\n"
        f"• 📝 Заметками\n"
        f"• 📋 Задачами\n"
        f"• 🎂 Днями рождения\n"
        f"• 🤖 AI помощником (ChatGPT)\n"
        f"• 🌐 Переводом текста\n"
        f"• 💼 HR рекомендациями\n\n"
        f"Чем могу помочь сегодня?"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

def get_user_name(message: Message, state_data: dict = None) -> str:
    """Получить имя пользователя из разных источников"""
    if state_data and state_data.get("user_name"):
        return state_data["user_name"]
    if message.from_user.last_name:
        return f"{message.from_user.first_name} {message.from_user.last_name}"
    return message.from_user.first_name or "друг"


@router.message(F.voice)
async def handle_voice_whisper(message: Message, state: FSMContext):
    """Обработка голосовых сообщений через Whisper API"""

    # Получаем имя пользователя из состояния
    data = await state.get_data()
    user_name = data.get("user_name", message.from_user.first_name)

    current_state = await state.get_state()
    is_translate_mode = (current_state == TranslateState.waiting_for_text)
    is_ai_mode = (current_state == GPTStates.waiting_for_question)

    if not is_translate_mode and not is_ai_mode:
        await message.answer(
            f"🎤 {user_name}, сначала выберите режим:\n"
            "• 🌐 Переводчик\n"
            "• 🤖 AI Помощник"
        )
        return

    processing_msg = await message.answer(f"🎤 Слушаю, {user_name}... Распознаю голосовое сообщение...")

    try:
        # Скачиваем голосовое сообщение
        file = await message.bot.get_file(message.voice.file_id)

        # Скачиваем файл в bytes
        voice_bytes = await message.bot.download_file(file.file_path)

        # ВАЖНО: преобразуем bytes в BytesIO и правильно именуем файл
        audio_file = io.BytesIO(voice_bytes.read())
        audio_file.name = f"voice_{message.from_user.id}.ogg"

        # Сбрасываем указатель в начало
        audio_file.seek(0)

        # Используем OpenAI Whisper для распознавания
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )

        # Получаем распознанный текст
        recognized_text = transcript.text

        await processing_msg.edit_text(f"🎤 {user_name}, вы сказали: {recognized_text}")

        # Обработка в зависимости от режима
        if is_translate_mode:
            prompt = f"Переведи следующий текст на русский язык (если текст не на русском) или исправь ошибки (если на русском):\n\n{recognized_text}"
            translation = await gpt_service.get_response(prompt, max_tokens=500, temperature=0.3)

            if translation and not translation.startswith("❌"):
                await message.answer(
                    f"📝 *Исходный текст:*\n{recognized_text}\n\n"
                    f"🌐 *Результат:*\n{translation}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(f"❌ {user_name}, не удалось обработать текст.\n\n{translation}")

        elif is_ai_mode:
            data = await state.get_data()
            edit_mode = data.get("edit_mode", False)
            summarize_mode = data.get("summarize_mode", False)

            if edit_mode:
                prompt = f"Отредактируй следующий текст, исправь ошибки, сделай более понятным. Пользователя зовут {user_name}:\n\n{recognized_text}"
                response_prefix = "✍️ Отредактированный текст:\n\n"
            elif summarize_mode:
                prompt = f"Сделай краткое резюме текста. Пользователя зовут {user_name}:\n\n{recognized_text}"
                response_prefix = "📝 Резюме:\n\n"
            else:
                prompt = recognized_text
                response_prefix = "🤖 Ответ:\n\n"

            response = await gpt_service.get_response(prompt, max_tokens=1000, temperature=0.7)

            if response and not response.startswith("❌"):
                await message.answer(f"{response_prefix}{response}", parse_mode="Markdown")
            else:
                await message.answer(f"❌ {user_name}, ошибка: {response}")

        await state.clear()

    except Exception as e:
        logger.error(f"Whisper ошибка: {e}")
        await processing_msg.edit_text(
            f"❌ {user_name}, не удалось распознать голосовое сообщение.\n\n"
            f"Ошибка: {str(e)[:100]}\n\n"
            "Попробуйте:\n"
            "• Говорить четче\n"
            "• Отправить текстовое сообщение"
        )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    # Получаем имя пользователя
    user_name = message.from_user.first_name
    if message.from_user.last_name:
        user_name = f"{message.from_user.first_name} {message.from_user.last_name}"

    # Приветственное сообщение с именем
    welcome_text = (
        f"👋 *Добро пожаловать, {user_name}!*\n\n"
        f"Я помогу вам с:\n"
        f"• 📝 Заметками\n"
        f"• 📋 Задачами\n"
        f"• 🎂 Днями рождения\n"
        f"• 🤖 AI помощником (ChatGPT)\n"
        f"• 🌐 Переводом текста\n"
        f"• 💼 HR рекомендациями\n\n"
        f"Чем могу помочь сегодня?"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard
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


@router.message(F.text == "🏠 Главное меню")
async def back_to_main_menu_text(message: Message, state: FSMContext):
    """Обработчик текстовой кнопки возврата в главное меню"""
    await state.clear()

    user_name = message.from_user.first_name
    welcome_text = (
        f"👋 *Добро пожаловать обратно, {user_name}!*\n\n"
        f"Выберите нужную функцию с помощью кнопок ниже:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )


@router.message(Command("ping"))
async def ping(message: Message):
    """Проверка работоспособности"""
    await message.answer("🏓 Pong! Бот работает.")


# Добавьте сохранение истории диалога
@router.message(GPTStates.waiting_for_question)
async def process_gpt_question(message: Message, state: FSMContext):
    data = await state.get_data()
    user_name = data.get("user_name", message.from_user.first_name)

    # Сохраняем историю
    history = data.get("conversation_history", [])
    history.append({"role": "user", "content": message.text})

    # Ограничиваем историю последними 10 сообщениями
    if len(history) > 10:
        history = history[-10:]

    # Добавляем системный промпт с именем пользователя
    system_prompt = f"Ты дружелюбный AI ассистент. Пользователя зовут {user_name}. Всегда обращайся к нему по имени в ответах."

    # Отправляем в GPT с контекстом
    response = await gpt_service.get_response_with_context(
        system_prompt=system_prompt,
        history=history,
        new_message=message.text
    )

    # Сохраняем ответ в историю
    history.append({"role": "assistant", "content": response})
    await state.update_data(conversation_history=history)

    await message.answer(f"🤖 {response}")

@router.callback_query()
async def debug_callbacks(callback: CallbackQuery):
    """Отладка всех callback запросов"""
    logger.info(f"🔘 Получен callback: '{callback.data}'")
    logger.info(f"   От пользователя: {callback.from_user.id}")
    logger.info(f"   Сообщение: {callback.message.text[:100] if callback.message.text else 'None'}")

    # Отвечаем, чтобы кнопка не "висела"
    await callback.answer(f"Получен callback: {callback.data}", show_alert=False)


@router.message(F.text)
async def debug_text_buttons(message: Message, state: FSMContext):
    """Отладка текстовых кнопок"""
    logger.info(f"🔘 Нажата кнопка: '{message.text}'")

    # Словарь соответствия кнопок и их обработчиков
    button_handlers = {
        "🤖 AI Помощник": "ai_menu_text_button",
        "🌐 Переводчик": "translate_text_button",
        "🦊 Показать лису": "show_fox_button",
        "🌤️ Погода": "weather_menu_button",
        "📋 Задачи": "tasks_menu_button",
        "🎂 Дни рождения": "birthdays_menu_button",
        "📝 Заметки": "notes_menu_button",
        "💼 HR Рекрутер": "hr_menu_button",
        "ℹ️ Информация": "info_button",
        "❓ Помощь": "help_button",
    }


@router.message()
async def catch_all_messages(message: Message, state: FSMContext):
    """Отладка: ловим все сообщения"""
    current_state = await state.get_state()

    logger.info("=" * 60)
    logger.info(f"📨 ПОЛУЧЕНО СООБЩЕНИЕ:")
    logger.info(f"   Текст: '{message.text}'")
    logger.info(f"   Тип: {message.content_type}")
    logger.info(f"   От пользователя: {message.from_user.id}")
    logger.info(f"   Состояние: {current_state}")
    logger.info("=" * 60)

    # Отвечаем на неизвестные команды
    if message.text and not message.text.startswith('/'):
        await message.answer(
            f"❓ Я получил сообщение: '{message.text}'\n\n"
            f"Состояние: {current_state or 'не выбрано'}\n\n"
            f"Пожалуйста, используйте кнопки меню для навигации.",
            reply_markup=main_keyboard
        )

@router.callback_query()
async def log_all_callbacks(callback: CallbackQuery):
    """Логирование всех callback для отладки"""
    logger.debug(f"Callback: {callback.data} from user {callback.from_user.id}")
    # Не вызываем callback.answer() здесь, чтобы не блокировать другие хэндлеры