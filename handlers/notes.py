from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
import json
import os
import re
import logging

from states.user_states import NoteState
from keyboards.keyboar import main_keyboard, back_keyboard, get_notes_reply_keyboard, get_ai_menu, get_hr_menu
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="notes")


# ============================================
# ПУТЬ К ФАЙЛУ ДЛЯ ХРАНЕНИЯ ЗАМЕТОК
# ============================================
# Для Amvera используем /data, для локальной разработки - папку data
def get_notes_file_path():
    """Определяет правильный путь для хранения заметок"""
    # Сначала проверяем постоянное хранилище Amvera
    if os.path.exists('/data') and os.access('/data', os.W_OK):
        notes_dir = '/data'
        logger.info("📁 Используется постоянное хранилище Amvera для заметок: /data")
    else:
        # Локальная разработка
        notes_dir = 'data'
        logger.info("📁 Используется локальное хранилище для заметок: data/")

    # Создаем директорию, если её нет
    if not os.path.exists(notes_dir):
        os.makedirs(notes_dir, exist_ok=True)

    return os.path.join(notes_dir, 'notes.json')


NOTES_FILE = get_notes_file_path()


def load_notes(user_id: int) -> list:
    """Загружает заметки пользователя"""
    if not os.path.exists(NOTES_FILE):
        return []

    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            all_notes = json.load(f)
            return all_notes.get(str(user_id), [])
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Ошибка загрузки заметок: {e}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при загрузке заметок: {e}")
        return []


def save_notes(user_id: int, notes: list):
    """Сохраняет заметки пользователя (атомарно)"""
    try:
        # Загружаем все заметки
        all_notes = {}
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    all_notes = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Файл заметок поврежден, создаем новый")
                all_notes = {}

        # Обновляем заметки пользователя
        all_notes[str(user_id)] = notes

        # Атомарная запись через временный файл
        temp_file = f"{NOTES_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(all_notes, f, ensure_ascii=False, indent=2)

        # Перемещаем временный файл
        os.replace(temp_file, NOTES_FILE)

    except Exception as e:
        logger.error(f"Ошибка сохранения заметок: {e}")
        raise


def get_notes_list_keyboard(notes: list, page: int = 0):
    """Клавиатура со списком заметок (пагинация)"""
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    page_notes = notes[start:end]

    buttons = []
    for i, note in enumerate(page_notes, start=start):
        title = note.get("title", "Без названия")[:30]
        buttons.append([InlineKeyboardButton(
            text=f"📄 {title}",
            callback_data=f"note_view:{i}"
        )])

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"note_page:{page - 1}"))
    if end < len(notes):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"note_page:{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 В меню", callback_data="note_menu_back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_note_actions_keyboard(note_id: int, note_title: str):
    """Инлайн клавиатура для действий с заметкой"""
    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"note_edit:{note_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"note_delete:{note_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="note_back_to_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================

@router.message(F.text == "📝 Создать заметку")
async def create_note_start(message: Message, state: FSMContext):
    """Начало создания заметки"""
    logger.info(f"📝 create_note_start вызван пользователем {message.from_user.id}")
    await state.set_state(NoteState.waiting_for_title)
    await message.answer(
        "📝 *Создание новой заметки*\n\n"
        "Введите *заголовок* заметки (максимум 50 символов):\n\n"
        "или отправьте /cancel для отмены",
        reply_markup=back_keyboard,
        parse_mode="Markdown"
    )


@router.message(NoteState.waiting_for_title, F.text)
async def create_note_title(message: Message, state: FSMContext):
    """Получение заголовка заметки"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Создание заметки отменено.", reply_markup=get_notes_reply_keyboard())
        return

    title = message.text.strip()

    if len(title) > 50:
        await message.answer("❌ Заголовок слишком длинный (максимум 50 символов). Попробуйте снова:")
        return

    if len(title) < 1:
        await message.answer("❌ Заголовок не может быть пустым. Попробуйте снова:")
        return

    await state.update_data(note_title=title)
    await state.set_state(NoteState.waiting_for_content)
    await message.answer(
        f"✅ Заголовок: *{title}*\n\n"
        "Теперь введите *содержание* заметки:\n\n"
        "💡 *Совет:* Используйте `#теги` для удобного поиска\n\n"
        "или отправьте /cancel для отмены",
        parse_mode="Markdown"
    )


@router.message(NoteState.waiting_for_content, F.text)
async def create_note_content(message: Message, state: FSMContext):
    """Получение содержания и сохранение заметки"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Создание заметки отменено.", reply_markup=get_notes_reply_keyboard())
        return

    content = message.text.strip()

    if not content:
        await message.answer("❌ Содержание заметки не может быть пустым. Введите текст:")
        return

    data = await state.get_data()
    title = data.get("note_title")

    # Извлекаем теги из содержания
    tags = re.findall(r'#(\w+)', content)

    # Создаем заметку
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = {
        "id": int(datetime.now().timestamp()),
        "title": title,
        "content": content,
        "tags": tags,
        "created_at": now,
        "updated_at": now
    }

    # Сохраняем
    user_id = message.from_user.id
    notes = load_notes(user_id)
    notes.append(note)
    save_notes(user_id, notes)

    await state.clear()

    tags_text = f"\n🏷️ Теги: {', '.join(f'#{t}' for t in tags)}" if tags else ""

    await message.answer(
        f"✅ *Заметка создана!*\n\n"
        f"📌 *Заголовок:* {title}\n"
        f"🕐 *Создано:* {now}{tags_text}",
        reply_markup=get_notes_reply_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "📋 Мои заметки")
async def list_notes(message: Message):
    """Показать список заметок"""
    logger.info(f"📋 list_notes вызван пользователем {message.from_user.id}")
    user_id = message.from_user.id
    notes = load_notes(user_id)

    if not notes:
        await message.answer(
            "📭 У вас пока нет заметок.\n\n"
            "Используйте кнопку '📝 Создать заметку', чтобы добавить первую заметку.",
            reply_markup=get_notes_reply_keyboard()
        )
        return

    # Безопасная сортировка (защита от None в created_at)
    notes.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    save_notes(user_id, notes)

    await message.answer(
        f"📋 *Ваши заметки* (всего: {len(notes)})\n\n"
        "Выберите заметку для просмотра:",
        reply_markup=get_notes_list_keyboard(notes),
        parse_mode="Markdown"
    )


# ============================================
# CALLBACK ОБРАБОТЧИКИ
# ============================================

@router.callback_query(F.data.startswith("note_page:"))
async def notes_page_callback(callback: CallbackQuery):
    """Обработка пагинации списка заметок"""
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка пагинации")
        return

    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    await callback.message.edit_text(
        f"📋 *Ваши заметки* (всего: {len(notes)})\n\n"
        f"Страница {page + 1}",
        reply_markup=get_notes_list_keyboard(notes, page),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("note_view:"))
async def view_note_callback(callback: CallbackQuery):
    """Просмотр заметки"""
    try:
        note_index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка")
        return

    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if note_index >= len(notes):
        await callback.answer("❌ Заметка не найдена")
        return

    note = notes[note_index]

    tags_text = f"\n🏷️ Теги: {', '.join(f'#{t}' for t in note.get('tags', []))}" if note.get('tags') else ""

    note_text = (
        f"📄 *{note.get('title', 'Без названия')}*\n\n"
        f"📝 *Содержание:*\n"
        f"{note.get('content', '')}\n\n"
        f"🕐 *Создано:* {note.get('created_at', 'Неизвестно')}\n"
        f"✏️ *Обновлено:* {note.get('updated_at', 'Неизвестно')}{tags_text}"
    )

    await callback.message.edit_text(
        note_text,
        reply_markup=get_note_actions_keyboard(note_index, note.get('title', '')),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "note_back_to_list")
async def back_to_notes_list(callback: CallbackQuery):
    """Возврат к списку заметок"""
    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    await callback.message.edit_text(
        f"📋 *Ваши заметки* (всего: {len(notes)})",
        reply_markup=get_notes_list_keyboard(notes),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "note_menu_back")
async def back_to_notes_menu(callback: CallbackQuery):
    """Возврат в меню заметок"""
    await callback.message.delete()
    await callback.message.answer(
        "📝 *Управление заметками*\n\n"
        "Здесь вы можете создавать, просматривать и управлять своими заметками.",
        reply_markup=get_notes_reply_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================
# ПОИСК И УДАЛЕНИЕ
# ============================================

@router.message(F.text == "🔍 Поиск заметок")
async def search_notes_start(message: Message, state: FSMContext):
    """Начало поиска заметок"""
    logger.info(f"🔍 search_notes_start вызван пользователем {message.from_user.id}")
    await state.set_state(NoteState.waiting_for_search)
    await message.answer(
        "🔍 *Поиск заметок*\n\n"
        "Введите слово или фразу для поиска:\n"
        "• Можно использовать #теги\n"
        "• Поиск происходит по заголовку и содержанию\n\n"
        "или отправьте /cancel для отмены",
        reply_markup=back_keyboard,
        parse_mode="Markdown"
    )


@router.message(NoteState.waiting_for_search, F.text)
async def search_notes_execute(message: Message, state: FSMContext):
    """Выполнение поиска заметок"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Поиск отменен.", reply_markup=get_notes_reply_keyboard())
        return

    query = message.text.strip().lower()
    user_id = message.from_user.id
    notes = load_notes(user_id)

    if not notes:
        await message.answer("📭 У вас пока нет заметок.", reply_markup=get_notes_reply_keyboard())
        await state.clear()
        return

    # Поиск
    results = []
    for note in notes:
        title = (note.get("title") or "").lower()
        content = (note.get("content") or "").lower()
        tags = [t.lower() for t in (note.get("tags") or [])]

        if (query in title or
                query in content or
                any(query in tag or query == f"#{tag}" for tag in tags) or
                (query.startswith("#") and query[1:] in tags)):
            results.append(note)

    await state.clear()

    if not results:
        await message.answer(
            f"🔍 *Результаты поиска*\n\n"
            f"По запросу *'{query}'* ничего не найдено.\n\n"
            f"Попробуйте другие ключевые слова.",
            reply_markup=get_notes_reply_keyboard(),
            parse_mode="Markdown"
        )
        return

    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    response = f"🔍 *Результаты поиска*\n\n"
    response += f"🔎 Запрос: *'{query}'*\n"
    response += f"📊 Найдено: *{len(results)}* заметок\n\n"

    for i, note in enumerate(results[:5], 1):
        response += f"{i}. *{note.get('title', 'Без названия')}*\n"
        content_preview = note.get('content', '')[:50]
        response += f"   📝 {content_preview}...\n" if len(note.get('content', '')) > 50 else f"   📝 {content_preview}\n"
        if note.get('tags'):
            response += f"   🏷️ {', '.join(f'#{t}' for t in note.get('tags', []))}\n"
        response += "\n"

    if len(results) > 5:
        response += f"... и еще {len(results) - 5} заметок"

    await message.answer(response, reply_markup=get_notes_reply_keyboard(), parse_mode="Markdown")


@router.message(F.text == "🗑️ Удалить заметку")
async def delete_note_menu(message: Message):
    """Меню удаления заметок"""
    logger.info(f"🗑️ delete_note_menu вызван пользователем {message.from_user.id}")
    user_id = message.from_user.id
    notes = load_notes(user_id)

    if not notes:
        await message.answer(
            "📭 У вас пока нет заметок для удаления.",
            reply_markup=get_notes_reply_keyboard()
        )
        return

    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    await message.answer(
        f"🗑️ *Выберите заметку для удаления*\n\n"
        f"Всего заметок: {len(notes)}",
        reply_markup=get_notes_list_keyboard(notes),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("note_edit:"))
async def edit_note_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования заметки"""
    try:
        note_index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка")
        return

    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if note_index >= len(notes):
        await callback.answer("❌ Заметка не найдена")
        return

    note = notes[note_index]

    await state.update_data(edit_note_index=note_index)
    await state.set_state(NoteState.waiting_for_content)

    await callback.message.edit_text(
        f"✏️ *Редактирование заметки*\n\n"
        f"📌 *Заголовок:* {note.get('title')}\n\n"
        f"📝 *Текущее содержание:*\n{note.get('content')}\n\n"
        f"Введите новое содержание заметки:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(NoteState.waiting_for_content, F.text)
async def save_edited_note(message: Message, state: FSMContext):
    """Сохранение отредактированной заметки"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено.", reply_markup=get_notes_reply_keyboard())
        return

    new_content = message.text.strip()

    if not new_content:
        await message.answer("❌ Содержание заметки не может быть пустым. Введите текст:")
        return

    data = await state.get_data()
    note_index = data.get("edit_note_index")
    user_id = message.from_user.id
    notes = load_notes(user_id)

    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if note_index is None or note_index >= len(notes):
        await message.answer("❌ Ошибка: заметка не найдена", reply_markup=get_notes_reply_keyboard())
        await state.clear()
        return

    # Обновляем теги
    tags = re.findall(r'#(\w+)', new_content)

    # Обновляем заметку
    notes[note_index]["content"] = new_content
    notes[note_index]["tags"] = tags
    notes[note_index]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_notes(user_id, notes)

    await state.clear()
    await message.answer(
        f"✅ *Заметка обновлена!*\n\n"
        f"📌 *Заголовок:* {notes[note_index].get('title')}",
        reply_markup=get_notes_reply_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("note_delete:"))
async def delete_note_confirm(callback: CallbackQuery):
    """Подтверждение удаления заметки"""
    try:
        note_index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"note_confirm_delete:{note_index}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="note_cancel_delete")]
    ])

    await callback.message.edit_text(
        "⚠️ *Вы уверены, что хотите удалить эту заметку?*\n\n"
        "Это действие нельзя отменить.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("note_confirm_delete:"))
async def delete_note_execute(callback: CallbackQuery):
    """Выполнение удаления заметки"""
    try:
        note_index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка")
        return

    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if note_index < len(notes):
        deleted_note = notes.pop(note_index)
        save_notes(user_id, notes)
        await callback.message.edit_text(
            f"✅ *Заметка удалена*\n\n"
            f"Удалена заметка: *{deleted_note.get('title')}*",
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text("❌ Ошибка: заметка не найдена")

    await callback.answer()


@router.callback_query(F.data == "note_cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    """Отмена удаления заметки"""
    user_id = callback.from_user.id
    notes = load_notes(user_id)
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    await callback.message.edit_text(
        f"📋 *Ваши заметки* (всего: {len(notes)})",
        reply_markup=get_notes_list_keyboard(notes),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============================================
# ОБРАБОТЧИК ОТМЕНЫ (только для заметок)
# ============================================
@router.message(Command("cancel"))
async def cancel_notes_handler(message: Message, state: FSMContext):
    """Отмена текущей операции (только для заметок)"""
    current_state = await state.get_state()
    if current_state is None:
        # Не показываем сообщение, если нет активного состояния
        return

    await state.clear()
    await message.answer(
        "✅ Операция отменена.",
        reply_markup=get_notes_reply_keyboard()
    )