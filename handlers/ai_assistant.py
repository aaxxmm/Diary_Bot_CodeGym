import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.user_states import TranslateState, GPTStates
from utils.gpt_service import gpt_service
from keyboards.keyboar import main_keyboard, get_ai_menu

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
    await state.update_data(ai_mode="chat", edit_mode=False, summarize_mode=False)

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


@router.message(GPTStates.waiting_for_question, F.text)
async def process_ai_request(message: Message, state: FSMContext):
    """Обработка AI запросов (только текст)"""

    text = message.text.strip()

    if not text:
        await message.answer("❌ Пожалуйста, напишите вопрос или текст для обработки.")
        return

    # Получаем данные из состояния
    data = await state.get_data()
    user_name = data.get("user_name", message.from_user.first_name)
    edit_mode = data.get("edit_mode", False)
    summarize_mode = data.get("summarize_mode", False)

    # Показываем, что бот печатает
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        if edit_mode:
            prompt = f"Отредактируй следующий текст, исправь ошибки, сделай более понятным. Пользователя зовут {user_name}:\n\n{text}"
            response = await gpt_service.get_response(prompt)
            await message.answer(f"✍️ *Отредактированный текст:*\n\n{response}", parse_mode="Markdown")

        elif summarize_mode:
            prompt = f"Сделай краткое резюме текста. Пользователя зовут {user_name}:\n\n{text}"
            response = await gpt_service.get_response(prompt)
            await message.answer(f"📝 *Резюме:*\n\n{response}", parse_mode="Markdown")

        else:
            # Обычный чат с GPT с персонализацией
            prompt = f"Пользователя зовут {user_name}. Ответь на вопрос, обращаясь по имени: {text}"
            response = await gpt_service.get_response(prompt)
            await message.answer(f"🤖 {response}", parse_mode="Markdown")

        # Очищаем состояние после обработки
        await state.clear()

    except Exception as e:
        logger.error(f"AI обработка ошибка: {e}")
        await message.answer(f"❌ {user_name}, произошла ошибка: {str(e)[:100]}")


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