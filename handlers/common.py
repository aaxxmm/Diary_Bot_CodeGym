from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import main_keyboard, back_keyboard
from keyboards.keyboar import main_keyboard, back_keyboard, get_notes_reply_keyboard, get_ai_menu, get_hr_menu
from utils.random_picture import fox
from config import settings

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.chat.first_name}! 👋\n\n"
        "Я твой персональный помощник.\n\n"
        "📌 Вот что я умею:\n"
        "• 📋 Ежедневник с событиями\n"
        "• 🎂 Напоминания о днях рождения\n"
        "• 📝 Заметки в общую группу\n"
        "• 💼 HR Рекрутер (AI)\n"
        "• 🌐 Переводчик (AI)\n"
        "• 🌤️ Прогноз погоды\n\n"
        "Используй кнопки ниже для навигации 👇",
        reply_markup=main_keyboard
    )


@router.message(F.text == "🏠 Главное меню")
async def back_to_main(message: Message):
    await message.answer("Главное меню:", reply_markup=main_keyboard)

# /info
@router.message(Command("info"))
async def command_info(message: Message):
    await message.answer(
        '🤖 *Информация о боте*\n\n'
        'Это бот с подключением ChatGPT и функциями:\n'
        '• 🦊 Случайные фото лис\n'
        '• 🌤️ Прогноз погоды\n'
        '• 💬 Общение с ChatGPT\n'
        '• 📋 Управление задачами\n'
        '• 🎂 Дни рождения',
        parse_mode=None
    )

@router.message(F.text == "🦊 Показать лису")
async def show_fox(message: Message):
    image_fox = await fox()
    if image_fox:
        await message.answer_photo(image_fox)
        await message.answer("🦊 Вот вам лиса! Понравилось?")
    else:
        await message.answer("❌ Не удалось получить фото лисы. Попробуйте позже.")


@router.message(F.text == "🌤️ Погода")
async def weather_menu(message: Message, state: FSMContext):
    from keyboards.menu import get_weather_menu
    await state.clear()  # Очищаем состояние
    await message.answer(
        "🌤️ Выберите действие:",
        reply_markup=get_weather_menu().as_markup()
    )


@router.message(F.text == "📋 Задачи")
async def tasks_menu(message: Message, state: FSMContext):
    from keyboards.menu import get_tasks_menu
    await state.clear()
    await message.answer(
        "📋 Управление задачами:",
        reply_markup=get_tasks_menu().as_markup()
    )


@router.message(F.text == "🎂 Дни рождения")
async def birthdays_menu(message: Message, state: FSMContext):
    from keyboards.menu import get_birthdays_menu
    await state.clear()
    await message.answer(
        "🎂 Управление днями рождения:",
        reply_markup=get_birthdays_menu().as_markup()
    )


@router.message(F.text == "📝 Заметки")
async def notes_menu(message: Message, state: FSMContext):
    # Исправлено: используем правильную функцию
    await state.clear()
    await message.answer(
        "📝 *Управление заметками*\n\n"
        "Здесь вы можете создавать, просматривать и управлять своими заметками.\n\n"
        "📌 *Доступные действия:*\n"
        "• 📝 Создать заметку\n"
        "• 📋 Просмотреть все заметки\n"
        "• 🔍 Найти заметку по тексту или тегам\n"
        "• 🗑️ Удалить заметку",
        reply_markup=get_notes_reply_keyboard(),
        parse_mode="Markdown"
    )

# /help
@router.message(Command('help'))
async def general_help(message: Message):
    help_text = (
        "📋 *Доступные команды:*\n\n"
        "/start - Начать работу\n"
        "/help - Показать эту справку\n"
        "/info - Информация о боте\n"
        "/fox - Случайное фото лисы\n"
        "/weather_help - Помощь по погоде\n\n"
        "🌤️ **Для погоды:**\n"
        "• Просто напишите название любого города\n"
        "• Например: Москва, Астана, Минск\n\n"
        "📋 **Для задач:**\n"
        "• Используйте кнопки в главном меню\n\n"
        "🎂 **Для дней рождений:**\n"
        "• Используйте кнопки в главном меню"
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(
    F.text.in_([
        "💼 HR Рекрутер",
        "HR Рекрутер",
        "Hr рекрутёр",
        "hr рекрутер"
    ])
)
async def hr_menu(message: Message, state: FSMContext):
    from keyboards import get_hr_menu
    await state.clear()

    # Импортируем состояния из career_choice
    from handlers.career_choice import CareerChoice

    await message.answer(
        "💼 **HR Рекрутер помощник**\n\n"
        "Я помогу вам с выбором карьеры и развитием навыков!\n\n"
        "Доступные команды:\n"
        "• /prof - выбрать профессию\n"
        "• /skills - оценить навыки\n"
        "• /recommend - получить рекомендации\n\n"
        "Или используйте кнопки ниже:",
        reply_markup=get_hr_menu().as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text == "🤖 AI Помощник")
async def ai_menu(message: Message, state: FSMContext):
    from keyboards.keyboard import get_ai_menu  # Исправлено
    await state.clear()
    await message.answer(
        "🤖 *AI Помощник*\n\n"
        "Доступные функции:\n"
        "• 🌐 Перевод текста\n"
        "• ✍️ Редактирование текста\n"
        "• 📝 Резюме заметок",
        reply_markup=get_ai_menu().as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text == "🌐 Переводчик")
async def translate_menu(message: Message, state: FSMContext):
    # Устанавливаем состояние для перевода
    from states.user_states import TranslateState
    await state.set_state(TranslateState.waiting_for_text)
    await message.answer(
        "🌐 Отправьте текст для перевода (можно голосовое сообщение):\n\n"
        "Пример: 'Hello, how are you?'\n"
        "или отправьте голосовое сообщение",
        reply_markup=back_keyboard
    )

#обработчик голосовых команд
from aiogram.types import Voice
from aiogram import F
import io
from pydub import AudioSegment
import speech_recognition as sr


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Обработка голосовых сообщений"""
    voice: Voice = message.voice

    # Скачиваем голосовое сообщение
    file = await message.bot.get_file(voice.file_id)
    voice_bytes = await message.bot.download_file(file.file_path)

    # Конвертируем для распознавания
    audio = AudioSegment.from_file(io.BytesIO(voice_bytes.read()))

    # Распознаем речь
    recognizer = sr.Recognizer()
    with io.BytesIO() as wav_io:
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                await message.answer(f"🎤 Распознано: {text}")
                # Обрабатываем команды из голоса
                await process_voice_command(message, text, state)
            except:
                await message.answer("❌ Не удалось распознать речь. Попробуйте еще раз или используйте текст.")


from aiogram.types import CallbackQuery


@router.callback_query(F.data.startswith("hr:"))
async def hr_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback-запросов для HR функций"""
    action = callback.data.split(":")[1]

    if action == "career_choice":
        # Перенаправляем на выбор профессии
        from handlers.career_choice import command_prof
        # Создаем фейковое сообщение
        class FakeMessage:
            def __init__(self, chat_id, bot):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.bot = bot
                self.from_user = callback.from_user

       #fake_msg = FakeMessage(callback.message.chat.id, callback.bot)
       #await command_prof(fake_msg, state)

    elif action == "learning":
        profession = callback.data.split(":")[2]
        await callback.message.answer(
            f"📚 **Курсы для {profession}:**\n\n"
            f"• Coursera - специализированные курсы\n"
            f"• Stepik - бесплатные уроки\n"
            f"• YouTube - практические туториалы\n"
            f"• Habr - статьи и обзоры",
            parse_mode="Markdown"
        )

    elif action == "jobs":
        profession = callback.data.split(":")[2]
        await callback.message.answer(
            f"💼 **Где искать вакансии {profession}:**\n\n"
            f"• hh.ru - ведущий сайт по поиску работы\n"
            f"• LinkedIn - международные вакансии\n"
            f"• Habr Career - IT специализация\n"
            f"• Telegram-каналы по вашей профессии",
            parse_mode="Markdown"
        )
    await callback.answer()

@router.message()
async def fallback_handler(message: Message):
    """Catch-all handler for any unprocessed messages"""
    await message.answer(
        "❓ Я не понимаю эту команду.\n\n"
        "Пожалуйста, используйте кнопки меню для навигации:",
        reply_markup=main_keyboard
    )