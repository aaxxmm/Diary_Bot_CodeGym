from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Reply-клавиатуры (обычные кнопки)
button_start = KeyboardButton(text="🏠 Главное меню")
button_fox = KeyboardButton(text="🦊 Показать лису")
button_weather = KeyboardButton(text="🌤️ Погода")
button_tasks = KeyboardButton(text="📋 Задачи")
button_birthdays = KeyboardButton(text="🎂 Дни рождения")
button_notes = KeyboardButton(text="📝 Заметки")
button_ai = KeyboardButton(text="🤖 AI Помощник")
button_hr = KeyboardButton(text="💼 HR Рекрутер")
button_translate = KeyboardButton(text="🌐 Переводчик")
button_info = KeyboardButton(text="ℹ️ Информация")
button_help = KeyboardButton(text="❓ Помощь")

# Главная клавиатура (4 ряда по 2 кнопки)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button_fox, button_weather],
        [button_tasks, button_birthdays],
        [button_notes, button_ai],
        [button_hr, button_translate],
        [button_info, button_help],
    ],
    resize_keyboard=True
)

# Клавиатура для отмены/возврата
back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[button_start]],
    resize_keyboard=True
)


## Reply-клавиатура для заметок (для обычных кнопок)
def get_notes_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура меню заметок (Reply кнопки)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать заметку")],
            [KeyboardButton(text="📋 Мои заметки")],
            [KeyboardButton(text="🔍 Поиск заметок")],
            [KeyboardButton(text="🗑️ Удалить заметку")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


# Inline-клавиатуры (под кнопками сообщений)
def get_notes_inline_menu() -> InlineKeyboardBuilder:
    """Меню заметок (Inline кнопки)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать заметку", callback_data="note:create")
    builder.button(text="📋 Мои заметки", callback_data="note:list")
    builder.button(text="🔍 Найти заметку", callback_data="note:search")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder

def get_hr_menu() -> InlineKeyboardBuilder:
    """Меню HR рекрутера"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 Выбрать профессию", callback_data="hr:career_choice")
    builder.button(text="📊 Мои навыки", callback_data="hr:skills")
    builder.button(text="🎯 Рекомендации", callback_data="hr:recommendations")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder


def get_ai_menu() -> InlineKeyboardBuilder:
    """Меню AI помощника"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Перевод текста", callback_data="ai:translate")
    builder.button(text="✍️ Редактирование текста", callback_data="ai:edit")
    builder.button(text="📝 Резюме заметок", callback_data="ai:summarize")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder

def get_cancel_inline_keyboard():
    """Инлайн клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_inline_keyboard():
    """Инлайн клавиатура для отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="menu:ai")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()