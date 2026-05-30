
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import storage
from states.user_states import TaskStates
from keyboards.menu import get_cancel_button, get_task_action_keyboard, get_postpone_keyboard

from config import settings

router = Router(name="tasks")
logger = logging.getLogger(__name__)


def format_task_list(tasks, show_actions: bool = False, page: int = 1, per_page: int = 5) -> tuple:
    """Format tasks list for display with pagination"""
    if not tasks:
        return "📋 *У вас нет активных задач*", None

    total_pages = (len(tasks) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_tasks = tasks[start:end]

    text = "📋 *Ваши активные задачи:*\n\n"

    for i, task in enumerate(page_tasks, start + 1):
        deadline_dt = datetime.fromisoformat(task.deadline)
        days_left = task.days_until_deadline()

        if days_left < 0:
            status_emoji = "🔴"
            time_str = f"просрочена на {abs(days_left)} дн."
        elif days_left == 0:
            status_emoji = "🟠"
            time_str = "сегодня"
        elif days_left == 1:
            status_emoji = "🟡"
            time_str = "завтра"
        else:
            status_emoji = "🟢"
            time_str = f"через {days_left} дн."

        text += f"{status_emoji} *{i}. {task.title}*\n"
        if task.description:
            text += f"   📝 {task.description[:50]}\n"
        text += f"   ⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')} ({time_str})\n"

        if show_actions:
            text += f"   🔔 Напоминание: за {task.reminder_minutes} мин.\n"
        text += "\n"

    # Create pagination keyboard
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="◀️ Назад", callback_data=f"tasks:page:{page - 1}")
    if page < total_pages:
        builder.button(text="Вперед ▶️", callback_data=f"tasks:page:{page + 1}")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(2)

    return text, builder.as_markup() if builder.buttons else None


@router.callback_query(F.data == "menu:tasks")
async def show_tasks_menu(callback: CallbackQuery, state: FSMContext):
    """Show tasks menu"""
    await state.clear()

    user_id = callback.from_user.id
    active_tasks = storage.get_user_tasks(user_id, status='active')

    if not active_tasks:
        text = "📋 *У вас пока нет активных задач*\n\nХотите добавить новую задачу?"
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить задачу", callback_data="task:add")
        builder.button(text="🏠 Главное меню", callback_data="menu:main")
        builder.adjust(1)

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup()
        )
    else:
        text, keyboard = format_task_list(active_tasks, show_actions=False)
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить задачу", callback_data="task:add")
        builder.button(text="✏️ Управление задачами", callback_data="task:manage")
        builder.button(text="✅ Выполненные", callback_data="tasks:completed")
        builder.adjust(1)

        if keyboard:
            text += "\nВыберите задачу для управления:"
            # Add task selection buttons
            for i, task in enumerate(active_tasks[:10], 1):
                builder.button(text=f"{i}. {task.title[:30]}", callback_data=f"task:select:{task.id}")
            builder.adjust(1)

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup()
        )
    await callback.answer()


@router.callback_query(F.data == "tasks:completed")
async def show_completed_tasks(callback: CallbackQuery):
    """Show completed tasks"""
    user_id = callback.from_user.id
    completed_tasks = storage.get_user_tasks(user_id, status='completed')

    if not completed_tasks:
        text = "📋 *У вас нет выполненных задач*"
    else:
        text = "✅ *Ваши выполненные задачи:*\n\n"
        for i, task in enumerate(completed_tasks[:20], 1):
            deadline_dt = datetime.fromisoformat(task.deadline)
            text += f"{i}. {task.title}\n"
            text += f"   ⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к задачам", callback_data="menu:tasks")
    builder.button(text="🗑 Очистить все", callback_data="tasks:clear_completed")
    builder.adjust(1)

    await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "task:add")
async def start_add_task(callback: CallbackQuery, state: FSMContext):
    """Start task creation process"""
    await state.set_state(TaskStates.waiting_for_task_title)

    await callback.message.edit_text(
        text="➕ *Создание новой задачи*\n\n"
             "Введите *название задачи* (обязательно):\n\n"
             "Например: Купить продукты, Сделать отчет, Позвонить клиенту",
        reply_markup=get_cancel_button().as_markup()
    )
    await callback.answer()


@router.message(TaskStates.waiting_for_task_title)
async def process_task_title(message: Message, state: FSMContext):
    """Process task title"""
    if not message.text or len(message.text) > 100:
        await message.answer("❌ Название не должно быть пустым или превышать 100 символов. Попробуйте еще раз:")
        return

    await state.update_data(title=message.text.strip())
    await state.set_state(TaskStates.waiting_for_task_description)

    await message.answer(
        "📝 Введите *описание задачи* (необязательно):\n\n"
        "Можете пропустить, отправив '-'",
        reply_markup=get_cancel_button().as_markup()
    )


@router.message(TaskStates.waiting_for_task_description)
async def process_task_description(message: Message, state: FSMContext):
    """Process task description"""
    description = message.text.strip()
    if description == "-":
        description = ""

    await state.update_data(description=description)
    await state.set_state(TaskStates.waiting_for_task_deadline)

    await message.answer(
        "⏰ Введите *дату и время дедлайна*:\n\n"
        "Формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
        "Пример: `25.12.2024 18:00`\n\n"
        "Или укажите относительное время:\n"
        "• `+1d` - через 1 день\n"
        "• `+2h` - через 2 часа\n"
        "• `+30m` - через 30 минут",
        parse_mode="Markdown",
        reply_markup=get_cancel_button().as_markup()
    )


@router.message(TaskStates.waiting_for_task_deadline)
async def process_task_deadline(message: Message, state: FSMContext):
    """Process task deadline"""
    text = message.text.strip()
    deadline = None

    # Parse relative time
    if text.startswith('+'):
        try:
            value = int(text[1:-1])
            unit = text[-1].lower()

            if unit == 'h':
                deadline = datetime.now() + timedelta(hours=value)
            elif unit == 'd':
                deadline = datetime.now() + timedelta(days=value)
            elif unit == 'm':
                deadline = datetime.now() + timedelta(minutes=value)
            else:
                raise ValueError()
        except:
            pass

    # Parse absolute date
    if not deadline:
        try:
            deadline = datetime.strptime(text, "%d.%m.%Y %H:%M")
            if deadline < datetime.now():
                await message.answer("❌ Дедлайн не может быть в прошлом! Введите корректную дату:")
                return
        except:
            await message.answer(
                "❌ Неверный формат!\n\n"
                "Используйте: `ДД.ММ.ГГГГ ЧЧ:ММ`\n"
                "Или относительное время: `+1d`, `+2h`, `+30m`",
                parse_mode="Markdown"
            )
            return

    await state.update_data(deadline=deadline.isoformat())
    await state.set_state(TaskStates.waiting_for_task_reminder)

    await message.answer(
        "🔔 За сколько минут *напомнить* о задаче?\n\n"
        "Введите число минут (по умолчанию 60):\n"
        "• 15 - за 15 минут\n"
        "• 60 - за час\n"
        "• 1440 - за день",
        reply_markup=get_cancel_button().as_markup()
    )


@router.message(TaskStates.waiting_for_task_reminder)
async def process_task_reminder(message: Message, state: FSMContext):
    """Process reminder setting"""
    try:
        reminder_minutes = int(message.text.strip())
        if reminder_minutes < 1:
            reminder_minutes = 60
    except:
        reminder_minutes = 60

    data = await state.get_data()

    task = storage.add_task(
        user_id=message.from_user.id,
        title=data['title'],
        description=data.get('description', ''),
        deadline=datetime.fromisoformat(data['deadline']),
        reminder_minutes=reminder_minutes
    )

    deadline_dt = datetime.fromisoformat(task.deadline)

    success_text = (
        f"✅ *Задача добавлена!*\n\n"
        f"📌 *{task.title}*\n"
        f"📝 {task.description if task.description else '—'}\n"
        f"⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔔 Напомнить за {task.reminder_minutes} мин."
    )

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои задачи", callback_data="menu:tasks")
    builder.button(text="➕ Добавить еще", callback_data="task:add")
    builder.adjust(1)

    await message.answer(success_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "task:manage")
async def manage_tasks(callback: CallbackQuery):
    """Show tasks that can be managed"""
    user_id = callback.from_user.id
    active_tasks = storage.get_user_tasks(user_id, status='active')

    if not active_tasks:
        await callback.answer("Нет активных задач для управления")
        return

    builder = InlineKeyboardBuilder()
    for task in active_tasks[:10]:
        deadline_dt = datetime.fromisoformat(task.deadline)
        status = "🔴" if task.is_overdue() else "🟢"
        builder.button(
            text=f"{status} {task.title[:30]} ({deadline_dt.strftime('%d.%m')})",
            callback_data=f"task:select:{task.id}"
        )
    builder.button(text="◀️ Назад", callback_data="menu:tasks")
    builder.adjust(1)

    await callback.message.edit_text(
        text="✏️ *Выберите задачу для управления:*",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:select:"))
async def select_task(callback: CallbackQuery):
    """Show task details and actions"""
    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    task = storage.get_task(user_id, task_id)
    if not task:
        await callback.answer("Задача не найдена")
        return

    # Безопасное получение атрибутов
    title = task.title or "Без названия"
    description = task.description or "Нет описания"

    deadline_dt = datetime.fromisoformat(task.deadline)
    days_left = task.days_until_deadline()

    if days_left < 0:
        status_text = f"🔴 Просрочена на {abs(days_left)} дней"
    elif days_left == 0:
        status_text = "🟠 Сегодня"
    else:
        status_text = f"🟢 Осталось {days_left} дней"

    text = (
        f"📌 *{task.title}*\n\n"
        f"📝 {task.description if task.description else 'Нет описания'}\n\n"
        f"⏰ Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Статус: {status_text}\n"
        f"🔄 Отложено: {task.postponed_count} раз\n\n"
        f"Что хотите сделать с задачей?"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_task_action_keyboard(task_id).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:complete:"))
async def complete_task(callback: CallbackQuery):
    """Mark task as completed"""
    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    if storage.update_task_status(user_id, task_id, 'completed'):
        await callback.answer("✅ Задача выполнена!")
        await manage_tasks(callback)
    else:
        await callback.answer("❌ Ошибка при выполнении задачи")


@router.callback_query(F.data.startswith("task:postpone_menu:"))
async def show_postpone_menu(callback: CallbackQuery):
    """Show postpone options"""
    task_id = int(callback.data.split(":")[2])

    await callback.message.edit_reply_markup(
        reply_markup=get_postpone_keyboard(task_id).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:postpone:"))
async def postpone_task(callback: CallbackQuery):
    """Postpone task"""
    parts = callback.data.split(":")
    task_id = int(parts[2])
    minutes = int(parts[3])
    user_id = callback.from_user.id

    if storage.postpone_task(user_id, task_id, minutes):
        await callback.answer(f"⏰ Задача отложена на {minutes} минут!")
        await select_task(callback)
    else:
        await callback.answer("❌ Ошибка при откладывании")


@router.callback_query(F.data.startswith("task:delete_confirm:"))
async def confirm_delete_task(callback: CallbackQuery):
    """Confirm task deletion"""
    task_id = int(callback.data.split(":")[2])

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"task:delete:{task_id}")
    builder.button(text="❌ Отмена", callback_data=f"task:select:{task_id}")
    builder.adjust(1)

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("task:delete:"))
async def delete_task(callback: CallbackQuery):
    """Delete task"""
    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    if storage.delete_task(user_id, task_id):
        await callback.answer("🗑 Задача удалена!")
        await manage_tasks(callback)
    else:
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data.startswith("tasks:page:"))
async def tasks_pagination(callback: CallbackQuery):
    """Handle task pagination"""
    page = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    tasks = storage.get_user_tasks(user_id, status='active')

    text, keyboard = format_task_list(tasks, show_actions=False, page=page)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "tasks:clear_completed")
async def clear_completed_tasks(callback: CallbackQuery):
    """Clear all completed tasks"""
    user_id = callback.from_user.id
    completed_tasks = storage.get_user_tasks(user_id, status='completed')

    for task in completed_tasks:
        storage.delete_task(user_id, task.id)

    await callback.answer("✅ Все выполненные задачи удалены")
    await show_completed_tasks(callback)