
# Импортируем все роутеры
from .common import router as common_router
from .weather import router as weather_router
from .tasks import router as tasks_router
from .birthdays import router as birthdays_router
from .notes import router as notes_router
from .ai_assistant import router as ai_assistant_router
from .career_choice import router as career_router
from .translate import router as translate_router

# Список всех роутеров (без дублей)
all_routers = [
    notes_router,
    translate_router,
    weather_router,
    tasks_router,
    birthdays_router,
    career_router,
    common_router,
    ai_assistant_router,
]

# Логируем количество подключенных роутеров
print(f"✅ Загружено {len(all_routers)} роутеров")
print(f"Роутеры: {[r.name if hasattr(r, 'name') else 'unnamed' for r in all_routers]}")