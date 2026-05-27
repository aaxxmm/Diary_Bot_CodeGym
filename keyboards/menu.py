
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

def get_main_menu() -> InlineKeyboardBuilder:
    """Main menu with all features"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📋 Задачи", callback_data="menu:tasks")
    builder.button(text="🎂 Дни рождения", callback_data="menu:birthdays")
    builder.button(text="🌤 Погода", callback_data="menu:weather")
    builder.button(text="🤖 ChatGPT", callback_data="menu:gpt")
    builder.button(text="❓ Помощь", callback_data="menu:help")

    builder.adjust(2, 2, 2, 2, 1)
    return builder


def get_cancel_button() -> InlineKeyboardBuilder:
    """Cancel button for operations"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder


def get_tasks_menu() -> InlineKeyboardBuilder:
    """Tasks menu"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить задачу", callback_data="task:add")
    builder.button(text="📋 Список задач", callback_data="menu:tasks")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder


def get_birthdays_menu() -> InlineKeyboardBuilder:
    """Birthdays menu"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data="bd:add")
    builder.button(text="📋 Список", callback_data="menu:birthdays")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder


def get_task_action_keyboard(task_id: int) -> InlineKeyboardBuilder:
    """Task action buttons"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Выполнить", callback_data=f"task:complete:{task_id}")
    builder.button(text="⏰ Отложить", callback_data=f"task:postpone_menu:{task_id}")
    builder.button(text="🗑 Удалить", callback_data=f"task:delete_confirm:{task_id}")
    builder.button(text="◀️ Назад", callback_data="menu:tasks")

    builder.adjust(2, 1, 1)
    return builder


def get_postpone_keyboard(task_id: int) -> InlineKeyboardBuilder:
    """Postpone options keyboard"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🕐 1 час", callback_data=f"task:postpone:{task_id}:60")
    builder.button(text="🕓 3 часа", callback_data=f"task:postpone:{task_id}:180")
    builder.button(text="📆 1 день", callback_data=f"task:postpone:{task_id}:1440")
    builder.button(text="📆 2 дня", callback_data=f"task:postpone:{task_id}:2880")
    builder.button(text="📆 1 неделя", callback_data=f"task:postpone:{task_id}:10080")
    builder.button(text="◀️ Назад", callback_data=f"task:actions:{task_id}")

    builder.adjust(2, 2, 2, 1)
    return builder


def get_weather_menu() -> InlineKeyboardBuilder:
    """Weather menu"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌡 Текущая погода", callback_data="weather:current")
    builder.button(text="📅 Прогноз на 5 дней", callback_data="weather:forecast")
    builder.button(text="⚙️ Изменить город", callback_data="weather:change_city")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder