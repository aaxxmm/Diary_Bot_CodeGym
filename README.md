Diary Bot — Многофункциональный Telegram-бот

[![Python 3.14](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.4.1-green.svg)](https://docs.aiogram.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Telegram-бот для ведения заметок, управления задачами, отслеживания дней рождения, получения прогноза погоды и многого другого с использованием AI (GPT).

## ✨ Возможности

- 📝 **Заметки** — создание, поиск, удаление и хранение заметок
- 📋 **Задачи** — управление задачами с дедлайнами и напоминаниями
- 🎂 **Дни рождения** — отслеживание дней рождения и автоматические уведомления
- 🌤️ **Погода** — прогноз погоды по городу
- 🤖 **AI помощник** — перевод, редактирование текста, резюмирование заметок (GPT)
- 💼 **HR рекрутер** — выбор профессии и оценка навыков
- 🦊 **Случайная лиса** — получение случайных картинок с лисами
- 🎤 **Голосовые сообщения** — распознавание речи через Whisper API


## 🚀 Локальный запуск

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/YOUR_USERNAME/diary_bot_CodeGym.git
   cd diary_bot_CodeGym

### Создайте виртуальное окружение

    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # или
    venv\Scripts\activate  # Windows
            
    ### Установите зависимости      

### Установка зависимостей

    pip install python-dotenv
    pip install aiogram

### Фиксирование зависимостей
    pip freeze > requirements.txt
    pip install -r requirements.txt

### Настройте переменные окружения

    cp .env.example .env
    # Отредактируйте .env, добавьте ваш токен Telegram

### Необходимые переменные:

   TOKEN_TG — токен Telegram бота (обязательно)

   TOKEN_OPENAI — API ключ OpenAI (для GPT и Whisper)
   
   WEATHER_APP_TOKEN — API ключ OpenWeatherMap
   
   ADMIN_USER_ID — ваш Telegram ID (для администрирования)

### Запустите бота
   
   python main.py

###  структура проекта

    diary_bot_CodeGym/
    │
    ├── .github/                    # GitHub Actions (CI/CD)                     
    │   └── workflows/
    │       └── deploy.yml
    │
    ├── handlers/                         # Обработчики команд и сообщений
    │   ├── __init__.py                   # Экспорт всех роутеров
    │   ├── ai_assistant.py               # AI функции (GPT, перевод, редактирование)
    │   ├── birthdays.py                  # Дни рождения (CRUD, уведомления)
    │   ├── career_choice.py              # HR рекрутер (профессии, навыки)
    │   ├── common.py                     # Общие команды (/start, /help, кнопки)
    │   ├── error_handler.py              # Глобальная обработка ошибок
    │   ├── notes.py                      # Заметки (CRUD, теги, поиск)
    │   ├── tasks.py                      # Задачи (CRUD, дедлайны)
    │   ├── translate.py                  # Перевод текста (через GPT)
    │   └── weather.py                    # Погода (текущая, прогноз)
    │
    ├── keyboards/                        # Клавиатуры (Reply и Inline)                   
    │   ├── __init__.py                   # Экспорт клавиатур
    │   ├── keyboard.py                   # Основные клавиатуры
    │   ├── menu.py                       # Меню для задач, погоды, дней рождения
    │   └── prof_keyboards.py             # Клавиатуры для HR рекрутера
    │             
    ├── scheduler/                        # Фоновые задачи                   
    │   ├── __init__.py
    │   └── tasks.py                      # Проверка дедлайнов и дней рождений
    │
    ├── states/                           # FSM состояния (конечные автоматы)                          
    │   ├── __init__.py                   # Экспорт состояний
    │   └──  user_states.py               # Все состояния (задачи, заметки, GPT и др.)

    │
    ├── utils/                            # Утилиты и сервисы                            
    │   ├── __init__.py                   # Экспорт утилит
    │   ├── gpt_service.py                # Работа с OpenAI API (GPT, Whisper)
    │   ├── random_picture.py             # Получение фото лис
    │   └── translate_service.py          # Перевод текста через GPT
    │
    ├── data/                             # Хранилище данных (JSON)                             
    │   ├── notes.json                    # Заметки пользователей
    │   └── .gitkeep                     
    │
    ├── .env.example                      # Пример переменных окружения                      
    ├── .gitignore                        # Исключения для Git                        
    ├── config.py                         # Конфигурация и настройки                         
    ├── main.py                           # Точка входа (запуск бота)                           
    ├── models.py                         # Модели данных (Task, Birthday) и Storage                         
    ├── requirements.txt                  # Зависимости Python                 
    ├── README.md                         # Документация                         
    ├── amvera.yml                        # Конфигурация для деплоя на Amvera                        
    ├── Dockerfile                        # Docker контейнер                       
    └── LICENSE                           # Лицензия MIT            

###   🛠️ Технологии
Python 3.11 — язык программирования

aiogram 3.x — фреймворк для Telegram Bot API

OpenAI API — GPT-3.5/4 для AI функций и Whisper для распознавания речи

OpenWeatherMap API — погода

APScheduler — фоновые задачи (напоминания)

aiohttp — асинхронные HTTP запросы

###  📄 Лицензия
Распространяется под лицензией MIT. Смотрите файл LICENSE для подробностей.

###  🙏 Благодарности
BotFather за создание ботов

Amvera Cloud за хостинг

OpenAI за GPT API и Whisper

###  ⭐ Обратная связь
Если проект был полезен, поставьте звезду на GitHub!

По вопросам и предложениям: Telegram