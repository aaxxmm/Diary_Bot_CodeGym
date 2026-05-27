import logging
from datetime import datetime, timedelta
from aiogram import Bot

from models import storage

logger = logging.getLogger(__name__)


async def check_overdue_tasks(bot: Bot):
    """Check and notify about overdue tasks"""
    try:
        # Получаем копию user_id, чтобы избежать изменения во время итерации
        user_ids = list(storage.tasks.keys())

        for user_id in user_ids:
            tasks = storage.tasks.get(user_id, [])
            overdue_tasks = [t for t in tasks if t.is_overdue() and t.status == 'active']

            if not overdue_tasks:
                continue

            message = "⚠️ *Просроченные задачи:*\n\n"
            for task in overdue_tasks[:10]:  # Ограничиваем до 10 задач
                try:
                    deadline_dt = datetime.fromisoformat(task.deadline)
                    message += f"• *{task.title}*\n"
                    message += f"  Дедлайн: {deadline_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
                except Exception as e:
                    logger.error(f"Error formatting task {task.id}: {e}")
                    continue

            message += "Пожалуйста, обновите статус задач!"

            # Проверяем длину сообщения (Telegram лимит ~4096)
            if len(message) > 4000:
                message = message[:4000] + "\n... (список сокращен)"

            try:
                await bot.send_message(user_id, message, parse_mode="Markdown")
                logger.info(f"Sent overdue notification to user {user_id} ({len(overdue_tasks)} tasks)")
            except Exception as e:
                logger.error(f"Failed to send overdue notification to {user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_overdue_tasks: {e}")


async def check_upcoming_deadlines(bot: Bot):
    """Check and notify about upcoming deadlines"""
    try:
        now = datetime.now()
        # Увеличиваем окно до 30 минут, чтобы не пропустить уведомления
        notification_window = timedelta(minutes=30)

        user_ids = list(storage.tasks.keys())
        notified_count = 0

        for user_id in user_ids:
            tasks = storage.tasks.get(user_id, [])

            for task in tasks:
                if task.status != 'active':
                    continue

                try:
                    deadline = datetime.fromisoformat(task.deadline)
                    reminder_time = deadline - timedelta(minutes=task.reminder_minutes)

                    # Check if reminder should be sent now
                    if reminder_time <= now <= reminder_time + notification_window:
                        days_left = task.days_until_deadline()

                        if days_left < 0:
                            continue
                        elif days_left == 0:
                            time_str = "СЕГОДНЯ"
                        elif days_left == 1:
                            time_str = "ЗАВТРА"
                        else:
                            time_str = f"через {days_left} дней"

                        message = (
                            f"🔔 *Напоминание о задаче!*\n\n"
                            f"📌 *{task.title}*\n"
                            f"📝 {task.description[:200] if task.description else '—'}\n"
                            f"⏰ Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')} ({time_str})\n\n"
                            f"Не забудьте выполнить задачу!"
                        )

                        await bot.send_message(user_id, message, parse_mode="Markdown")
                        notified_count += 1
                        logger.info(f"Sent deadline reminder to user {user_id} for task {task.id}")

                        # Небольшая задержка, чтобы не превысить лимиты Telegram
                        await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Failed to process task {task.id} for user {user_id}: {e}")
                    continue

        if notified_count > 0:
            logger.info(f"Sent {notified_count} deadline reminders")

    except Exception as e:
        logger.error(f"Error in check_upcoming_deadlines: {e}")


async def check_birthdays(bot: Bot):
    """Check and notify about upcoming birthdays"""
    try:
        today = datetime.now().date()
        user_ids = list(storage.birthdays.keys())
        notified_count = 0

        for user_id in user_ids:
            birthdays = storage.birthdays.get(user_id, [])

            for birthday in birthdays:
                if not birthday.notification_enabled:
                    continue

                try:
                    days_until = birthday.days_until_next()
                    next_bday = birthday.get_next_birthday()

                    # Send notification 1 day before
                    if days_until == 1:
                        message = (
                            f"🎂 *Напоминание о дне рождения!*\n\n"
                            f"👤 *{birthday.name}*\n"
                            f"📅 Завтра, {next_bday.strftime('%d.%m')}!"
                        )

                        if birthday.year:
                            age = birthday.get_age()
                            if age is not None:
                                message += f"\n🎂 Будет {age + 1} лет!"

                        await bot.send_message(user_id, message, parse_mode="Markdown")
                        notified_count += 1
                        logger.info(f"Sent birthday reminder to user {user_id} for {birthday.name}")

                    # Send notification on the birthday
                    elif days_until == 0:
                        message = (
                            f"🎉 *СЕГОДНЯ ДЕНЬ РОЖДЕНИЯ!* 🎉\n\n"
                            f"👤 *{birthday.name}*\n"
                            f"📅 {next_bday.strftime('%d.%m')}\n\n"
                            f"Не забудьте поздравить!"
                        )

                        if birthday.year:
                            age = birthday.get_age()
                            if age is not None:
                                message += f"\n🎂 Исполняется {age + 1 if days_until == 1 else age} лет!"

                        await bot.send_message(user_id, message, parse_mode="Markdown")
                        notified_count += 1
                        logger.info(f"Sent birthday notification to user {user_id} for {birthday.name}")

                except Exception as e:
                    logger.error(f"Failed to process birthday {birthday.id} for user {user_id}: {e}")
                    continue

        if notified_count > 0:
            logger.info(f"Sent {notified_count} birthday notifications")

    except Exception as e:
        logger.error(f"Error in check_birthdays: {e}")


# Импортируем asyncio для sleep
import asyncio