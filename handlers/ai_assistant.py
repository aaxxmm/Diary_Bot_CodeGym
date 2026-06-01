import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.user_states import TranslateState, GPTStates
from utils.gpt_service import gpt_service
from keyboards.keyboar import main_keyboard, back_keyboard, get_ai_menu, get_hr_menu
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="ai_assistant")


def get_cancel_inline_keyboard():
    """Инлайн клавиатура для отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="menu:ai")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "ai:translate")
async def ai_translate_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки перевода в AI меню"""
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
    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(edit_mode=True, ai_mode="edit")

    await callback.message.edit_text(
        "✍️ *AI Редактирование текста*\n\n"
        "Отправьте текст, который нужно отредактировать.\n\n"
        "Я могу:\n"
        "• Исправить грамматические ошибки\n"
        "• Улучшить стиль текста\n"
        "• Сделать текст более профессиональным\n"
        "• Адаптировать под определенную аудиторию\n\n"
        "Просто напишите текст, который хотите отредактировать:",
        parse_mode="Markdown",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "ai:summarize")
async def ai_summarize_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки резюме заметок в AI меню"""
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


@router.callback_query(F.data == "menu:gpt")
async def show_gpt_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Show GPT menu"""
    logger.info("🟢 show_gpt_menu вызван")

    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(ai_mode="chat")  # Добавляем режим чата

    # Проверяем состояние
    current_state = await state.get_state()
    logger.info(f"State after set: {current_state}")

    text = (
        "🤖 <b>ChatGPT ассистент</b>\n\n"
        "Задайте мне любой вопрос, и я постараюсь на него ответить!\n\n"
        "Я могу помочь с:\n"
        "• Ответами на вопросы\n"
        "• Советами и рекомендациями\n"
        "• Объяснением сложных тем\n"
        "• Переводом текста\n"
        "• И многое другое!\n\n"
        "Просто напишите ваш вопрос ниже:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()


@router.message(GPTStates.waiting_for_question)
async def process_ai_request(message: Message, state: FSMContext):
    """Обработка AI запросов (редактирование, резюме, общие вопросы)"""
    text = message.text.strip()
    data = await state.get_data()

    # ДИАГНОСТИКА
    logger.info("=" * 50)
    logger.info("🔍 AI_ASSISTANT ОБНАРУЖИЛ ЗАПРОС!")
    logger.info(f"User ID: {message.from_user.id}")
    logger.info(f"Text: {message.text[:100] if message.text else 'None'}")
    logger.info("=" * 50)

    edit_mode = data.get("edit_mode", False)
    summarize_mode = data.get("summarize_mode", False)

    # Показываем индикатор набора текста
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    # Отправляем сообщение "Думаю..."
    thinking_msg = await message.answer("🤔 <b>Обрабатываю запрос...</b>\n\nПожалуйста, подождите...")

    # Формируем промпт в зависимости от режима
    if edit_mode:
        prompt = f"Отредактируй следующий текст: исправь грамматические и стилистические ошибки, сделай его более понятным и профессиональным. Верни только отредактированный текст, без пояснений:\n\n{text}"
        response_prefix = "✍️ <b>Отредактированный текст:</b>\n\n"
    elif summarize_mode:
        prompt = f"Сделай краткое резюме следующего текста. Выдели основные мысли и ключевую информацию. Верни только резюме, без пояснений:\n\n{text}"
        response_prefix = "📝 <b>Резюме:</b>\n\n"
    else:
        prompt = text
        response_prefix = "🤖 <b>Ответ:</b>\n\n"

    # Получаем ответ от GPT
    response = await gpt_service.get_response(prompt, max_tokens=1500, temperature=0.7)

    if response and not response.startswith("❌"):
        if len(response) > 4000:
            parts = [response[i:i + 4000] for i in range(0, len(response), 4000)]
            await thinking_msg.edit_text(
                text=f"{response_prefix}{parts[0]}"
            )
            for part in parts[1:]:
                await message.answer(part)
        else:
            await thinking_msg.edit_text(
                text=f"{response_prefix}{response}"
            )
    else:
        await thinking_msg.edit_text(
            text=f"❌ <b>Ошибка</b>\n\n{response if response else 'Не удалось обработать запрос. Пожалуйста, попробуйте позже.'}"
        )

    # Показываем клавиатуру для продолжения
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Новый запрос", callback_data="menu:ai")
    builder.button(text="🤖 Чат с GPT", callback_data="menu:gpt")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)

    await message.answer(
        "Что делаем дальше?",
        reply_markup=builder.as_markup()
    )

    await state.clear()
    logger.info(f"AI request processed for user {message.from_user.id}")


@router.callback_query(F.data == "menu:ai")
async def show_ai_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню AI помощника"""
    await state.clear()

    await callback.message.edit_text(
        "🤖 *AI Помощник*\n\n"
        "Выберите нужную функцию:\n\n"
        "• 🌐 *Перевод текста* - перевод на любой язык\n"
        "• ✍️ *Редактирование* - исправление ошибок, улучшение стиля\n"
        "• 📝 *Резюме* - краткое изложение текста\n"
        "• 💬 *Чат с GPT* - задайте любой вопрос\n\n"
        "Все функции используют искусственный интеллект GPT.",
        parse_mode="Markdown",
        reply_markup=get_ai_menu().as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    await callback.message.edit_text(
        "🏠 *Главное меню*\n\n"
        "Выберите нужную функцию:",
        parse_mode="Markdown"
    )

    # Отправляем новое сообщение с главной клавиатурой
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "gpt:clear")
async def clear_gpt_state(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear GPT conversation"""
    await state.clear()
    await callback.message.edit_text(
        text="✅ Диалог очищен. Можете задать новый вопрос!",
        reply_markup=get_cancel_inline_keyboard()
    )
    await callback.answer()