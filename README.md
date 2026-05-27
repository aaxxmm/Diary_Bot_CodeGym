Diary Bot — Многофункциональный Telegram-бот

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
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

### Локальный запуск

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

###  структура проекта

    diary_bot_CodeGym/
    │
    ├── .github/                          
    │   └── workflows/
    │       └── deploy.yml
    │
    ├── handlers/                        
    │   ├── __init__.py
    │   ├── ai_assistant.py
    │   ├── birthdays.py
    │   ├── career_choice.py
    │   ├── common.py
    │   ├── gpt.py
    │   ├── notes.py
    │   ├── tasks.py
    │   ├── translate.py
    │   └── weather.py
    │
    ├── keyboards/                     
    │   ├── __init__.py
    │   ├── keyboard.py                  
    │   ├── menu.py
    │   └── prof_keyboards.py
    │
    ├── scheduler/                        
    │   ├── __init__.py
    │   └── tasks.py
    │
    ├── states/                          
    │   ├── __init__.py
    │   ├── gpt_service1.py
    │   ├── translate_states.py
    │   ├── user_states.py
    │   └── weather_states.py
    │
    ├── utils/                            
    │   ├── __init__.py
    │   ├── gpt_service.py
    │   ├── random_picture.py
    │   └── translate_service.py
    │
    ├── data/                             
    │   ├── notes.json
    │   └── .gitkeep                     
    │
    ├── .env.example                      
    ├── .gitignore                        
    ├── config.py                         
    ├── main.py                           
    ├── models.py                         
    ├── requirements.txt                 
    ├── README.md                         
    ├── amvera.yml                        
    ├── Dockerfile                       
    └── LICENSE            

📄 Лицензия
Распространяется под лицензией MIT. Смотрите файл LICENSE для подробностей.

🙏 Благодарности
BotFather за создание ботов

Amvera Cloud за хостинг

OpenAI за GPT API

⭐ Не забудьте поставить звезду, если проект был полезен!