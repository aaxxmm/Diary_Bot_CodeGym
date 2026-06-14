
import re

from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from config import settings
from keyboards.keyboar import get_hr_menu
from keyboards import make_row_keyboard

router = Router(name="career_choice")

available_jobs = [
    '🐍 Программист Python',
    '💻 Программист Java',
    '🎨 UI/UX Дизайнер',
    '📊 Маркетолог',
    '📈 Менеджер продукта',
    '🔧 DevOps инженер',
    '🤖 AI специалист',
    '📱 iOS разработчик',
    '🤵 HR менеджер',
]

available_grades = [
    '🌱 Junior (0-1 года)',
    '🌿 Middle (1-3 лет)',
    '🌳 Senior (5+ лет)',
    '👨‍💼 Team Lead',
]

available_skills = {
    'Программист Python': ['Python', 'Django', 'FastAPI', 'SQL', 'Git', 'Docker', 'REST API'],
    'Программист Java': ['Java', 'Spring Boot', 'Hibernate', 'Maven', 'JUnit', 'SQL', 'Git'],
    'UI/UX Дизайнер': ['Figma', 'Adobe XD', 'Photoshop', 'Illustrator', 'UX Research', 'Prototyping', 'User Testing'],
    'Маркетолог': ['SEO', 'SMM', 'Google Analytics', 'Content Strategy', 'Email Marketing', 'PPC', 'CRM'],
    'Менеджер продукта': ['Agile', 'Scrum', 'Product Roadmap', 'User Stories', 'Jira', 'Analytics', 'A/B Testing'],
    'DevOps инженер': ['Linux', 'Docker', 'Kubernetes', 'Jenkins', 'AWS/GCP', 'Terraform', 'CI/CD'],
    'AI специалист': ['Python', 'TensorFlow', 'PyTorch', 'Machine Learning', 'Deep Learning', 'Pandas', 'NumPy'],
    'iOS разработчик': ['Swift', 'UIKit', 'SwiftUI', 'Core Data', 'Git', 'REST API', 'App Store Connect'],
    'HR менеджер': ['Recruiting', 'Onboarding', 'HRIS', 'Employee Relations', 'Performance Management', 'Labor Law'],
}

class CareerChoice(StatesGroup):
    job = State()
    grade = State()
    skills = State()

@router.message(Command('prof'))
async def command_prof(message: types.Message, state: FSMContext):
    """Обработчик команды /prof"""
    await message.answer(
        '**Выберите профессию**\n\n'
        'Я помогу вам определить подходящий уровень и дам рекомендации:',
        reply_markup=make_row_keyboard(available_jobs),
        parse_mode="Markdown"
    )
    await state.set_state(CareerChoice.job)

def extract_profession_name(profession_with_emoji: str) -> str:
    """Извлекает название профессии без эмодзи"""
    # Убираем эмодзи и пробел после него
    # Удаляем эмодзи в начале строки
    cleaned = re.sub(r'^[🐍💻🎨📊📈🔧🤖📱🤵]\s*', '', profession_with_emoji)
    return cleaned.strip()

@router.message(Command('recommend'))
async def command_recommend(message: types.Message, state: FSMContext):
    """Обработчик команды /recommend"""
    await message.answer(
        '🎯 **Для получения рекомендаций**\n\n'
        'Пожалуйста, выберите профессию:',
        reply_markup=make_row_keyboard(available_jobs),
        parse_mode="Markdown"
    )
    await state.set_state(CareerChoice.job)


@router.message(CareerChoice.job, F.text.in_(available_jobs))
async def prof_chosen(message: types.Message, state: FSMContext):
    # Сохраняем полное название профессии (с эмодзи)
    full_profession = message.text
    # Извлекаем имя без эмодзи для поиска в словарях
    clean_profession = extract_profession_name(full_profession)

    await state.update_data(profession=full_profession, clean_profession=clean_profession)

    await message.answer(
        f'📊 **Отлично!** Вы выбрали {clean_profession}\n\n'
        f'Теперь выберите ваш уровень опыта:',
        reply_markup=make_row_keyboard(available_grades),
        parse_mode="Markdown"
    )
    await state.set_state(CareerChoice.grade)


@router.message(CareerChoice.job)
async def prof_incorrect(message: types.Message):
    await message.answer(
        '❌ Пожалуйста, выберите профессию из списка ниже:',
        reply_markup=make_row_keyboard(available_jobs)
    )

@router.message(CareerChoice.grade, F.text.in_(available_grades))
async def grade_chosen(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    profession = user_data.get('profession')  # Полное название с эмодзи
    clean_profession = user_data.get('clean_profession')  # Название без эмодзи
    grade = message.text

    # Получаем рекомендации
    recommendations = generate_recommendations(clean_profession, grade)

    # Получаем навыки для этой профессии
    skills = available_skills.get(clean_profession, [])
    skills_text = "📚 **Рекомендуемые навыки:**\n" + "\n".join([f"• {skill}" for skill in skills]) if skills else ""

    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Курсы", callback_data=f"hr:learning:{clean_profession}")
    builder.button(text="💼 Вакансии", callback_data=f"hr:jobs:{clean_profession}")
    builder.button(text="📋 Навыки", callback_data=f"hr:skills:{clean_profession}")
    builder.button(text="🏠 В меню", callback_data="menu:main")
    builder.adjust(2)

    response_text = (
        f"✅ **Ваш профиль:**\n"
        f"Профессия: {clean_profession}\n"
        f"Уровень: {grade}\n\n"
        f"📋 **Рекомендации:**\n{recommendations}\n\n"
        f"{skills_text}"
    )

    await message.answer(
        response_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.clear()

@router.message(CareerChoice.grade)
async def grade_incorrect(message: types.Message):
    await message.answer(
        '❌ Пожалуйста, выберите уровень из списка ниже:',
        reply_markup=make_row_keyboard(available_grades)
    )


@router.callback_query(F.data.startswith("hr:skills:"))
async def show_skills_callback(callback: CallbackQuery):
    """Показать навыки для профессии по callback"""
    profession = callback.data.split(":")[2]
    skills = available_skills.get(profession, [])

    if skills:
        skills_text = f"📚 **Навыки для {profession}:**\n\n" + "\n".join([f"• {skill}" for skill in skills])
    else:
        skills_text = f"❌ Навыки для {profession} не найдены."

    await callback.message.answer(skills_text, parse_mode="Markdown")
    await callback.answer()


@router.message(Command('skills'))
async def show_skills(message: types.Message):
    """Показать все доступные навыки по профессиям"""
    skills_text = "📚 **Навыки по профессиям:**\n\n"
    for prof, skills in available_skills.items():
        skills_text += f"**{prof}:**\n"
        skills_text += "  • " + "\n  • ".join(skills) + "\n\n"

    # Разбиваем на части, если сообщение слишком длинное
    if len(skills_text) > 4000:
        # Отправляем по частям
        for i in range(0, len(skills_text), 4000):
            await message.answer(skills_text[i:i + 4000], parse_mode="Markdown")
    else:
        await message.answer(skills_text, parse_mode="Markdown")

@router.message(F.text == "🔙 Назад")
async def back_to_hr_menu(message: Message, state: FSMContext):
    """Возврат в HR меню"""
    from keyboards import get_hr_menu
    await state.clear()
    await message.answer(
        "💼 HR Рекрутер помощник\n\n"
        "Выберите действие:",
        reply_markup=get_hr_menu().as_markup()
    )


@router.callback_query(F.data == "hr:skills")
async def hr_skills_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Мои навыки' - показывает все навыки"""
    await callback.message.answer(
        "📊 **Все доступные навыки по профессиям:**\n\n"
        "Используйте команду /skills для просмотра полного списка навыков.",
        parse_mode="Markdown"
    )

    # Показываем список профессий для выбора
    builder = InlineKeyboardBuilder()
    for job in available_jobs:
        clean_name = extract_profession_name(job)
        builder.button(text=job, callback_data=f"hr:show_skills:{clean_name}")
    builder.button(text="◀️ Назад", callback_data="menu:main")
    builder.adjust(1)

    await callback.message.answer(
        "**Выберите профессию для просмотра навыков:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hr:show_skills:"))
async def show_skills_for_profession(callback: CallbackQuery):
    """Показать навыки для конкретной профессии"""
    profession = callback.data.split(":")[2]
    skills = available_skills.get(profession, [])

    if skills:
        skills_text = f"📚 **Навыки для {profession}:**\n\n" + "\n".join([f"• {skill}" for skill in skills])
    else:
        skills_text = f"❌ Навыки для {profession} не найдены."

    await callback.message.answer(skills_text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "hr:recommendations")
async def hr_recommendations_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Рекомендации' - перенаправляет на выбор профессии"""
    await callback.message.answer(
        "🎯 **Для получения персональных рекомендаций**\n\n"
        "Пожалуйста, выберите профессию и уровень опыта:",
        reply_markup=make_row_keyboard(available_jobs),
        parse_mode="Markdown"
    )
    await state.set_state(CareerChoice.job)
    await callback.answer()


@router.callback_query(F.data == "hr:career_choice")
async def hr_career_choice(callback: CallbackQuery, state: FSMContext):
    """Обработчик inline кнопки выбора профессии"""
    await callback.message.answer(
        '**Выберите профессию**\n\n'
        'Я помогу вам определить подходящий уровень и дам рекомендации:',
        reply_markup=make_row_keyboard(available_jobs),
        parse_mode="Markdown"
    )
    await state.set_state(CareerChoice.job)
    await callback.answer()

def generate_recommendations(profession: str, grade: str) -> str:
    """Генерация персональных рекомендаций"""

    # Определяем уровень (без эмодзи и описания)
    if 'Junior' in grade:
        level = 'Junior'
    elif 'Middle' in grade:
        level = 'Middle'
    elif 'Senior' in grade:
        level = 'Senior'
    else:
        level = 'Junior'

    # Рекомендации по уровням и профессиям
    recommendations_map = {
        'Junior': {
            'Программист Python': '📌 Изучайте основы алгоритмов и структур данных. Пройдите курсы на Stepik или Coursera. Начните участвовать в open-source проектах на GitHub. Создайте портфолио из 2-3 pet-проектов.',
            'Программист Java': '📌 Освойте Java Core, изучите Spring Boot. Решайте задачи на LeetCode. Создайте простой REST API проект. Изучайте паттерны проектирования.',
            'UI/UX Дизайнер': '📌 Создайте портфолио из 3-4 работ. Изучите принципы юзабилити. Пройдите курс по Figma. Изучайте работы известных дизайнеров на Behance.',
            'Маркетолог': '📌 Освойте Google Analytics и Яндекс.Метрику. Изучите основы SEO и SMM. Пройдите курс по таргетированной рекламе. Ведите свой блог для практики.',
            'Менеджер продукта': '📌 Изучите Agile и Scrum. Пройдите курс по управлению продуктами. Научитесь работать с Jira и Trello. Изучайте метрики продуктов.',
            'DevOps инженер': '📌 Освойте Linux, Docker, Git. Изучите основы CI/CD. Настройте простой pipeline на GitHub Actions. Изучайте облачные технологии.',
            'AI специалист': '📌 Изучите Python, библиотеки Pandas и NumPy. Пройдите курс по машинному обучению. Участвуйте в Kaggle соревнованиях.',
            'iOS разработчик': '📌 Изучите Swift и UIKit. Создайте простое приложение для App Store. Изучайте Human Interface Guidelines от Apple.',
            'HR менеджер': '📌 Изучите основы рекрутинга и HR процессов. Пройдите курс по трудовому праву. Изучайте HR-метрики и аналитику.',
        },
        'Middle': {
            'Программист Python': '🎯 Изучайте архитектуру приложений, асинхронное программирование. Освойте Docker и Kubernetes. Начните менторить джуниоров. Изучайте микросервисы.',
            'Программист Java': '🎯 Изучите микросервисную архитектуру, Kafka. Освойте Kubernetes. Улучшайте навыки тестирования. Изучайте паттерны микросервисов.',
            'UI/UX Дизайнер': '🎯 Развивайте навыки презентации дизайн-решений. Изучайте дизайн-системы. Проводите UX-исследования. Учитесь защищать свои решения.',
            'Маркетолог': '🎯 Осваивайте Data Science в маркетинге. Изучайте продуктовую аналитику. Разрабатывайте стратегии продвижения. Управляйте рекламными бюджетами.',
            'Менеджер продукта': '🎯 Развивайте навыки продуктовой аналитики. Изучайте A/B тестирование. Управляйте командой разработки. Разрабатывайте продуктовую стратегию.',
            'DevOps инженер': '🎯 Изучайте Kubernetes в деталях. Освойте Terraform. Настройте мониторинг (Prometheus + Grafana). Автоматизируйте процессы.',
            'AI специалист': '🎯 Изучайте глубокое обучение (CNN, RNN, Transformers). Освойте TensorFlow/PyTorch. Публикуйте статьи. Участвуйте в конференциях.',
            'iOS разработчик': '🎯 Изучите SwiftUI и Combine. Освойте Core Data и многопоточность. Оптимизируйте производительность приложений.',
            'HR менеджер': '🎯 Развивайте навыки HR-аналитики. Внедряйте системы оценки персонала. Управляйте HR-брендом. Автоматизируйте HR процессы.',
        },
        'Senior': {
            'Программист Python': '🏆 Станьте техническим лидом. Разрабатывайте архитектуру проектов. Ведите технические интервью. Публикуйте статьи и выступайте на конференциях.',
            'Программист Java': '🏆 Архитектура высоконагруженных систем. Наставничество. Оптимизация производительности. Техническое лидерство.',
            'UI/UX Дизайнер': '🏆 Управляйте дизайн-командой. Разрабатывайте дизайн-стратегию. Ведите переговоры с заказчиками. Развивайте направление дизайна.',
            'Маркетолог': '🏆 Разрабатывайте маркетинговые стратегии. Управляйте бюджетом отдела. Анализируйте ROI кампаний. Управляйте командой маркетологов.',
            'Менеджер продукта': '🏆 Управляйте портфелем продуктов. Разрабатывайте продуктовую стратегию компании. Управляйте бюджетом продукта.',
            'DevOps инженер': '🏆 Проектируйте инфраструктуру. Внедряйте GitOps. Оптимизируйте затраты в облаке. Управляйте командой DevOps.',
            'AI специалист': '🏆 Руководите AI-проектами. Разрабатывайте ML-стратегию. Публикуйте исследования в топовых конференциях.',
            'iOS разработчик': '🏆 Управляйте мобильной командой. Разрабатывайте архитектуру приложений. Оптимизируйте процессы разработки.',
            'HR менеджер': '🏆 Управляйте HR-стратегией компании. Разрабатывайте систему мотивации. Внедряйте HR-метрики. Управляйте HR-командой.',
        }
    }

    # Получаем рекомендацию
    if level in recommendations_map and profession in recommendations_map[level]:
        return recommendations_map[level][profession]

    # Общая рекомендация, если конкретная не найдена
    general_recommendations = {
        'Junior': '📌 Продолжайте учиться, выполняйте практические задачи, участвуйте в проектах, развивайте soft skills.',
        'Middle': '🎯 Развивайте экспертизу, берите ответственность за проекты, обучайте других, углубляйте технические навыки.',
        'Senior': '🏆 Делитесь опытом, развивайте лидерские качества, участвуйте в стратегическом планировании, будьте ментором.',
    }

    return general_recommendations.get(level, 'Продолжайте развиваться в выбранной области!')