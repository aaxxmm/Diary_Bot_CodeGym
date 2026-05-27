
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.gpt_service import gpt_service
from keyboards.menu import get_main_menu, get_cancel_button
from states.user_states import GPTStates
from config import settings

openai_api_key = settings.openai_api_key

router = Router(name="gpt")
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:gpt")
async def show_gpt_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Show GPT menu"""
    await state.set_state(GPTStates.waiting_for_question)
    await state.update_data(message_id=callback.message.message_id)

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
        reply_markup=get_cancel_button()
    )
    await callback.answer()

@router.message(GPTStates.waiting_for_question)
async def process_gpt_question(message: Message, state: FSMContext) -> None:
    """Process user question and get GPT response"""
    question = message.text.strip()

    # Сохраняем ID сообщения пользователя для последующего редактирования
    user_message_id = message.message_id

    # Показываем индикатор набора текста
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    # Отправляем сообщение "Думаю..."
    thinking_msg = await message.answer("🤔 <b>Думаю...</b>\n\nПожалуйста, подождите, ищу ответ...")

    # Получаем ответ от GPT
    response = await gpt_service.get_response(question)

    if response:
        # Форматируем ответ (разбиваем если слишком длинный)
        if len(response) > 4000:
            parts = [response[i:i + 4000] for i in range(0, len(response), 4000)]
            await thinking_msg.edit_text(
                text=f"🤖 <b>Ответ на ваш вопрос:</b>\n\n{parts[0]}"
            )
            for part in parts[1:]:
                await message.answer(part)
        else:
            await thinking_msg.edit_text(
                text=f"🤖 <b>Ответ на ваш вопрос:</b>\n\n{response}"
            )
    else:
        await thinking_msg.edit_text(
            text="❌ <b>Ошибка</b>\n\nНе удалось получить ответ. Пожалуйста, попробуйте позже."
        )

    await state.clear()
    logger.info(f"GPT question answered for user {message.from_user.id}")



@router.callback_query(F.data == "gpt:clear")
async def clear_gpt_state(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear GPT conversation"""
    await state.clear()
    await callback.message.edit_text(
        text="✅ Диалог очищен. Можете задать новый вопрос!",
        reply_markup=get_cancel_button()
    )
    await callback.answer()