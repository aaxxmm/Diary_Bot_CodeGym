import json
import os
import asyncio
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАТАМИ
# ============================================
def get_current_time():
    """Получение текущего времени с часовым поясом"""
    # Используем московское время для единообразия
    from config import settings
    try:
        import pytz
        tz = pytz.timezone(settings.default_timezone)
        return datetime.now(tz)
    except:
        # Fallback: UTC+3 для Москвы
        return datetime.now(timezone(timedelta(hours=3)))


def get_current_date():
    """Получение текущей даты с учетом часового пояса"""
    return get_current_time().date()


@dataclass
class Task:
    id: int
    user_id: int
    title: str
    description: str
    deadline: str  # ISO format
    reminder_minutes: int
    status: str  # 'active', 'completed', 'postponed'
    created_at: str
    postponed_count: int = 0

    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if self.status != 'active':
            return False
        try:
            deadline_dt = datetime.fromisoformat(self.deadline)
            current = get_current_time()
            # Если deadline без часового пояса, делаем его наивным для сравнения
            if deadline_dt.tzinfo is None:
                current_naive = current.replace(tzinfo=None)
                return current_naive > deadline_dt
            return current > deadline_dt
        except Exception as e:
            logger.error(f"Error checking overdue: {e}")
            return False

    def days_until_deadline(self) -> int:
        """Return days until deadline (negative if overdue)"""
        try:
            deadline_dt = datetime.fromisoformat(self.deadline)
            current = get_current_time()
            if deadline_dt.tzinfo is None:
                current_naive = current.replace(tzinfo=None)
                delta = deadline_dt - current_naive
            else:
                delta = deadline_dt - current
            return delta.days
        except:
            return 999


@dataclass
class Birthday:
    id: int
    user_id: int
    name: str
    birth_date: str  # MM-DD format
    year: Optional[int] = None  # birth year for age calculation
    notification_enabled: bool = True

    def get_next_birthday(self) -> date:
        """Calculate next birthday date"""
        today = get_current_date()
        birth_month, birth_day = map(int, self.birth_date.split('-'))
        next_birthday = date(today.year, birth_month, birth_day)

        if next_birthday < today:
            next_birthday = date(today.year + 1, birth_month, birth_day)

        return next_birthday

    def days_until_next(self) -> int:
        """Return days until next birthday"""
        next_bday = self.get_next_birthday()
        today = get_current_date()
        delta = next_bday - today
        return delta.days

    def get_age(self) -> Optional[int]:
        """Calculate age based on birth year"""
        if not self.year:
            return None

        today = get_current_date()
        birth_month, birth_day = map(int, self.birth_date.split('-'))
        birthday_this_year = date(today.year, birth_month, birth_day)

        age = today.year - self.year
        if today < birthday_this_year:
            age -= 1

        return age


class Storage:
    """Simple JSON file storage with async lock"""

    def __init__(self, file_path: str = None):
        # Определяем правильный путь для данных
        if file_path is None:
            # Для Amvera используем /data, для локальной разработки - текущую папку
            if os.path.exists('/data') and os.access('/data', os.W_OK):
                # Режим Amvera или Docker
                self.file_path = '/data/user_data.json'
                logger.info("📁 Используется постоянное хранилище: /data/user_data.json")
            else:
                # Локальная разработка
                self.file_path = 'user_data.json'
                logger.info("📁 Используется локальное хранилище: user_data.json")
        else:
            self.file_path = file_path

        self.tasks: Dict[int, List[Task]] = {}
        self.birthdays: Dict[int, List[Birthday]] = {}
        self._next_task_id: Dict[int, int] = {}
        self._next_birthday_id: Dict[int, int] = {}

        # Блокировка для предотвращения конкурентной записи
        self._lock = asyncio.Lock()

        self._load()

    def _ensure_directory_exists(self):
        """Создает директорию для файла данных, если её нет"""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"📁 Создана директория: {directory}")
            except Exception as e:
                logger.error(f"❌ Не удалось создать директорию {directory}: {e}")

    def _load(self):
        """Load data from JSON file"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Load tasks
                    tasks_data = data.get('tasks', {})
                    for user_id_str, tasks_list in tasks_data.items():
                        user_id = int(user_id_str)
                        self.tasks[user_id] = []
                        for task_data in tasks_list:
                            try:
                                self.tasks[user_id].append(Task(**task_data))
                            except Exception as e:
                                logger.warning(f"Ошибка загрузки задачи {task_data}: {e}")

                    # Load birthdays
                    birthdays_data = data.get('birthdays', {})
                    for user_id_str, birthdays_list in birthdays_data.items():
                        user_id = int(user_id_str)
                        self.birthdays[user_id] = []
                        for bday_data in birthdays_list:
                            try:
                                self.birthdays[user_id].append(Birthday(**bday_data))
                            except Exception as e:
                                logger.warning(f"Ошибка загрузки дня рождения {bday_data}: {e}")

                    # Load next IDs
                    self._next_task_id = {int(k): v for k, v in data.get('next_task_id', {}).items()}
                    self._next_birthday_id = {int(k): v for k, v in data.get('next_birthday_id', {}).items()}

                    logger.info(f"✅ Загружены данные для {len(self.tasks)} пользователей")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
                # Создаем бэкап поврежденного файла
                backup_path = f"{self.file_path}.backup"
                try:
                    os.rename(self.file_path, backup_path)
                    logger.warning(f"📁 Поврежденный файл сохранен как {backup_path}")
                except:
                    pass
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки данных: {e}")
        else:
            logger.info(f"📁 Файл данных не найден, будет создан при первом сохранении: {self.file_path}")

    async def _save(self):
        """Save data to JSON file with async lock"""
        async with self._lock:
            try:
                self._ensure_directory_exists()

                data = {
                    'tasks': {},
                    'birthdays': {},
                    'next_task_id': self._next_task_id,
                    'next_birthday_id': self._next_birthday_id
                }

                for user_id, tasks in self.tasks.items():
                    data['tasks'][str(user_id)] = [asdict(task) for task in tasks]

                for user_id, birthdays in self.birthdays.items():
                    data['birthdays'][str(user_id)] = [asdict(bday) for bday in birthdays]

                # Временный файл для атомарной записи
                temp_file = f"{self.file_path}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Перемещаем временный файл (атомарная операция)
                os.replace(temp_file, self.file_path)

                logger.debug(f"💾 Данные сохранены: {len(self.tasks)} пользователей")
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения данных: {e}")

    def _get_next_task_id(self, user_id: int) -> int:
        """Get next task ID for user"""
        current = self._next_task_id.get(user_id, 1)
        self._next_task_id[user_id] = current + 1
        return current

    def _get_next_birthday_id(self, user_id: int) -> int:
        """Get next birthday ID for user"""
        current = self._next_birthday_id.get(user_id, 1)
        self._next_birthday_id[user_id] = current + 1
        return current

    # ============================================
    # TASK METHODS
    # ============================================
    async def add_task(self, user_id: int, title: str, description: str,
                       deadline: datetime, reminder_minutes: int) -> Task:
        """Add new task for user"""
        # Конвертируем deadline в строку с ISO форматом
        if deadline.tzinfo is None:
            deadline_str = deadline.isoformat()
        else:
            deadline_str = deadline.isoformat()

        task = Task(
            id=self._get_next_task_id(user_id),
            user_id=user_id,
            title=title,
            description=description,
            deadline=deadline_str,
            reminder_minutes=reminder_minutes,
            status='active',
            created_at=get_current_time().isoformat(),
            postponed_count=0
        )

        if user_id not in self.tasks:
            self.tasks[user_id] = []

        self.tasks[user_id].append(task)
        await self._save()
        return task

    def get_user_tasks(self, user_id: int, status: Optional[str] = None) -> List[Task]:
        """Get user tasks, optionally filtered by status"""
        tasks = self.tasks.get(user_id, [])
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.deadline)

    def get_task(self, user_id: int, task_id: int) -> Optional[Task]:
        """Get specific task by ID"""
        for task in self.tasks.get(user_id, []):
            if task.id == task_id:
                return task
        return None

    async def update_task_status(self, user_id: int, task_id: int, status: str) -> bool:
        """Update task status"""
        task = self.get_task(user_id, task_id)
        if task:
            task.status = status
            await self._save()
            return True
        return False

    async def postpone_task(self, user_id: int, task_id: int, minutes: int) -> bool:
        """Postpone task by X minutes"""
        task = self.get_task(user_id, task_id)
        if task:
            from datetime import datetime, timedelta
            current_deadline = datetime.fromisoformat(task.deadline)
            new_deadline = current_deadline + timedelta(minutes=minutes)
            task.deadline = new_deadline.isoformat()
            task.postponed_count += 1
            await self._save()
            return True
        return False

    async def delete_task(self, user_id: int, task_id: int) -> bool:
        """Delete task"""
        tasks = self.tasks.get(user_id, [])
        for i, task in enumerate(tasks):
            if task.id == task_id:
                del tasks[i]
                await self._save()
                return True
        return False

    # ============================================
    # BIRTHDAY METHODS
    # ============================================
    async def add_birthday(self, user_id: int, name: str, birth_date: str, year: Optional[int] = None) -> Birthday:
        """Add new birthday"""
        birthday = Birthday(
            id=self._get_next_birthday_id(user_id),
            user_id=user_id,
            name=name,
            birth_date=birth_date,
            year=year
        )

        if user_id not in self.birthdays:
            self.birthdays[user_id] = []

        self.birthdays[user_id].append(birthday)
        await self._save()
        return birthday

    def get_user_birthdays(self, user_id: int) -> List[Birthday]:
        """Get all birthdays for user, sorted by next birthday"""
        birthdays = self.birthdays.get(user_id, [])
        return sorted(birthdays, key=lambda b: b.days_until_next())

    def get_birthday(self, user_id: int, birthday_id: int) -> Optional[Birthday]:
        """Get specific birthday by ID"""
        for bday in self.birthdays.get(user_id, []):
            if bday.id == birthday_id:
                return bday
        return None

    async def delete_birthday(self, user_id: int, birthday_id: int) -> bool:
        """Delete birthday"""
        birthdays = self.birthdays.get(user_id, [])
        for i, bday in enumerate(birthdays):
            if bday.id == birthday_id:
                del birthdays[i]
                await self._save()
                return True
        return False

    async def toggle_birthday_notification(self, user_id: int, birthday_id: int) -> bool:
        """Toggle notification setting"""
        bday = self.get_birthday(user_id, birthday_id)
        if bday:
            bday.notification_enabled = not bday.notification_enabled
            await self._save()
            return True
        return False


# Глобальный экземпляр хранилища
storage = Storage()