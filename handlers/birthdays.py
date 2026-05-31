
import logging
from datetime import datetime, date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import storage
from states.user_states import BirthdayStates
from keyboards.menu import get_cancel_button
from config import settings

router = Router(name="birthdays")
logger = logging.getLogger(__name__)


def format_birthdays_list(user_id: int) -> tuple:
    """Format birthdays list with upcoming sorted first"""
    birthdays = storage.get_user_birthdays(user_id)

    if not birthdays:
        return "🎂 *У вас нет добавленных дней рождений*\n\nДобавьте первый с помощью кнопки ниже!", None

    text = "🎂 *Список дней рождений:*\n\n"

    upcoming = [b for b in birthdays if b.days_until_next() >= 0]
    past = [b for b in birthdays if b.days_until_next() < 0]

    # Upcoming birthdays (soonest first)
    if upcoming:
        text += "📅 *Ближайшие:*\n"
        for bday in upcoming[:10]:
            days = bday.days_until_next()
            if days == 0:
                day_str = "🔴 СЕГОДНЯ!"
            elif days == 1:
                day_str = "🟠 ЗАВТРА!"
            elif days <= 7:
                day_str = f"🟡 через {days} дней"
            else:
                day_str = f"🟢 через {days} дней"

            age_info = ""
            if bday.get_age() is not None:
                next_age = bday.get_age() + 1 if bday.days_until_next() == 0 else bday.get_age() + 1
                age_info = f" (будет {next_age} лет)"

            text += f"• *{bday.name}*{age_info} — {bday.birth_date} — {day_str}\n"

    if past:
        text += "\n📜 *Остальные:*\n"
        for bday in past[:10]:
            text += f"• {bday.name} — {bday.birth_date}\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить день рождения", callback_data="bd:add")
    builder.button(text="🗑 Удалить", callback_data="bd:delete_menu")
    builder.button(text="🔔 Настройки уведомлений", callback_data="bd:settings")
    builder.button(text="🏠 Главное меню", callback_data="menu:main")
    builder.adjust(1)

    return text, builder.as_markup()


@router.callback_query(F.data == "menu:birthdays")
async def show_birthdays_menu(callback: CallbackQuery, state: FSMContext):
    """Show birthdays menu"""
    await state.clear()
    text, keyboard = format_birthdays_list(callback.from_user.id)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "bd:add")
async def start_add_birthday(callback: CallbackQuery, state: FSMContext):
    """Start adding birthday"""
    await state.set_state(BirthdayStates.waiting_for_name)

    await callback.message.edit_text(
        text="🎂 *Добавление дня рождения*\n\n"
             "Введите *имя человека*:\n\n"
             "Примеры: Мама, Папа, Иван Петров",
        reply_markup=get_cancel_button().as_markup()
    )
    await callback.answer()


@router.message(BirthdayStates.waiting_for_name)
async def process_birthday_name(message: Message, state: FSMContext):
    """Process birthday name"""
    name = message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await message.answer("❌ Имя должно быть от 1 до 50 символов. Попробуйте еще раз:")
        return

    await state.update_data(name=name)
    await state.set_state(BirthdayStates.waiting_for_date)

    await message.answer(
        "📅 Введите *дату рождения*:\n\n"
        "Формат: `ДД.ММ` или `ДД.ММ.ГГГГ`\n\n"
        "Примеры:\n"
        "• `15.05` — только день и месяц\n"
        "• `25.12.1990` — с годом рождения\n\n"
        "Если укажете год, будет рассчитываться возраст!",
        parse_mode="Markdown",
        reply_markup=get_cancel_button().as_markup()
    )


@router.message(BirthdayStates.waiting_for_date)
async def process_birthday_date(message: Message, state: FSMContext):
    """Process birthday date"""
    text = message.text.strip()
    year = None
    birth_date = None

    # Try parsing with year
    try:
        dt = datetime.strptime(text, "%d.%m.%Y")
        birth_date = dt.strftime("%m-%d")
        year = dt.year
        if year > date.today().year:
            await message.answer("❌ Год не может быть в будущем! Введите корректную дату:")
            return
    except:
        pass

    # Try parsing without year
    if not birth_date:
        try:
            dt = datetime.strptime(text, "%d.%m")
            birth_date = dt.strftime("%m-%d")
        except:
            await message.answer(
                "❌ Неверный формат!\n\n"
                "Используйте: `ДД.ММ` или `ДД.ММ.ГГГГ`\n"
                "Пример: `15.05` или `25.12.1990`",
                parse_mode="Markdown"
            )
            return

    data = await state.get_data()

    birthday = await storage.add_birthday(
        user_id=message.from_user.id,
        name=data['name'],
        birth_date=birth_date,
        year=year
    )

    await state.clear()

    success_text = (
        f"✅ *День рождения добавлен!*\n\n"
        f"👤 {birthday.name}\n"
        f"📅 {birthday.birth_date.replace('-', '.')}"
    )

    if year:
        success_text += f"\n🎂 Год рождения: {year}"
        age = birthday.get_age()
        if age is not None:
            success_text += f"\n📊 Возраст: {age} лет"

    builder = InlineKeyboardBuilder()
    builder.button(text="🎂 Список дней рождений", callback_data="menu:birthdays")
    builder.button(text="➕ Добавить еще", callback_data="bd:add")
    builder.adjust(1)

    await message.answer(success_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "bd:delete_menu")
async def show_birthday_delete_menu(callback: CallbackQuery):
    """Show birthdays to delete"""
    user_id = callback.from_user.id
    birthdays = storage.get_user_birthdays(user_id)

    if not birthdays:
        await callback.answer("Нет дней рождений для удаления")
        return

    builder = InlineKeyboardBuilder()
    for bday in birthdays[:15]:
        builder.button(
            text=f"🗑 {bday.name} — {bday.birth_date.replace('-', '.')}",
            callback_data=f"bd:delete_confirm:{bday.id}"
        )
    builder.button(text="◀️ Назад", callback_data="menu:birthdays")
    builder.adjust(1)

    await callback.message.edit_text(
        text="🗑 *Выберите день рождения для удаления:*",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bd:delete_confirm:"))
async def confirm_delete_birthday(callback: CallbackQuery):
    """Confirm birthday deletion"""
    birthday_id = int(callback.data.split(":")[2])
    bday = storage.get_birthday(callback.from_user.id, birthday_id)

    if not bday:
        await callback.answer("Запись не найдена")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"bd:delete:{birthday_id}")
    builder.button(text="❌ Отмена", callback_data="bd:delete_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        text=f"🗑 *Удалить день рождения {bday.name} ({bday.birth_date.replace('-', '.')})?*\n\n"
             f"Это действие нельзя отменить!",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bd:delete:"))
async def delete_birthday(callback: CallbackQuery):
    """Delete birthday"""
    birthday_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    if await storage.delete_birthday(user_id, birthday_id):
        await callback.answer("✅ День рождения удален!")
        await show_birthdays_menu(callback, None)
    else:
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data == "bd:settings")
async def show_birthday_settings(callback: CallbackQuery):
    """Show birthday notification settings"""
    user_id = callback.from_user.id
    birthdays = storage.get_user_birthdays(user_id)

    if not birthdays:
        await callback.answer("Нет дней рождений для настройки")
        await show_birthdays_menu(callback, None)
        return

    builder = InlineKeyboardBuilder()
    for bday in birthdays[:15]:
        status = "🔔 Вкл" if bday.notification_enabled else "🔕 Выкл"
        builder.button(
            text=f"{bday.name} ({bday.birth_date.replace('-', '.')}) — {status}",
            callback_data=f"bd:toggle:{bday.id}"
        )
    builder.button(text="◀️ Назад", callback_data="menu:birthdays")
    builder.adjust(1)

    await callback.message.edit_text(
        text="⚙️ *Настройки уведомлений*\n\n"
             "Нажмите на запись, чтобы включить/выключить напоминания:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bd:toggle:"))
async def toggle_birthday_notification(callback: CallbackQuery):
    """Toggle birthday notification setting"""
    birthday_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    if await storage.toggle_birthday_notification(user_id, birthday_id):
        await callback.answer("Настройки обновлены!")
        await show_birthday_settings(callback)
    else:
        await callback.answer("❌ Ошибка")