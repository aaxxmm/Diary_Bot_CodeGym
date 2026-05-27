
from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    """Task creation states"""
    waiting_for_task_title = State()
    waiting_for_task_description = State()
    waiting_for_task_deadline = State()
    waiting_for_task_reminder = State()
    waiting_for_task_name = State()
    waiting_for_task_date = State()
    waiting_for_task_time = State()


class BirthdayStates(StatesGroup):
    """Birthday creation states"""
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_reminder_mode = State()


class SettingsStates(StatesGroup):
    """Settings states"""
    waiting_for_city = State()
    waiting_for_timezone = State()


class WeatherStates(StatesGroup):
    """Weather states — ОБЪЕДИНЕНО из двух файлов"""
    waiting_for_city = State()      # Из user_states.py
    current_weather = State()       # Из weather_states.py
    forecast_weather = State()      # Из weather_states.py


class CurrencyStates(StatesGroup):
    """Currency states"""
    waiting_for_amount = State()
    waiting_for_currency = State()


class GPTStates(StatesGroup):
    """GPT chat states"""
    waiting_for_question = State()


class ImageStates(StatesGroup):
    """Image generation states"""
    waiting_for_prompt = State()


class TranslateState(StatesGroup):
    """Translation states"""
    waiting_for_text = State()


class NoteState(StatesGroup):
    """Note states"""
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_search = State()