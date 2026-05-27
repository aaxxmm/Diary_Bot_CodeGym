import math
import hashlib
import aiohttp
import asyncio
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from states.weather_states import WeatherStates
from keyboards.keyboar import main_keyboard, back_keyboard, get_notes_reply_keyboard, get_ai_menu, get_hr_menu
from config import settings, token_weather
from states.user_states import WeatherStates

router = Router()
logger = logging.getLogger(__name__)

# Исправлено: используем только settings
weather_token = settings.weather_token
default_city = settings.default_city

router = Router()

logger = logging.getLogger(__name__)

async def get_forecast(city: str) -> list:
    """Асинхронное получение прогноза погоды"""
    forecast_url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"q={city}&units=metric&appid={token_weather}&lang=ru"
    )

    timeout = aiohttp.ClientTimeout(total=15)  # Таймаут 15 секунд

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(forecast_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ошибка API {response.status}: {error_text}")

                data = await response.json()
                print("Forecast API response status:", response.status)

                if "list" in data:
                    return data["list"]
                else:
                    raise Exception(f"Ошибка получения прогноза. Ответ: {data.get('message', 'Неизвестная ошибка')}")
        except asyncio.TimeoutError:
            raise Exception("Превышено время ожидания ответа от API погоды")
        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка соединения с API погоды: {str(e)}")
        except ServerDisconnectedError as e:
            logger.error(f"🔌 Сервер разорвал соединение: {e}")
            # Переподнимаем исключение, чтобы обработать выше
            raise Exception(f"Сервер разорвал соединение: {str(e)}")


def aggregate_daily_forecast(forecasts: list) -> list:
    """Агрегирует 3-часовые прогнозы в дневные"""
    daily = {}

    for forecast in forecasts:
        dt_txt = forecast.get("dt_txt")
        if not dt_txt:
            continue

        # Извлекаем только дату (без времени)
        date_str = dt_txt.split(" ")[0]

        if date_str not in daily:
            # Первый прогноз за этот день
            daily[date_str] = {
                "dt": forecast["dt"],
                "main": {
                    "temp": forecast["main"]["temp"],
                    "temp_min": forecast["main"]["temp"],
                    "temp_max": forecast["main"]["temp"],
                    "feels_like": forecast["main"]["feels_like"],
                    "humidity": forecast["main"]["humidity"]
                },
                "weather": forecast["weather"],
                "wind": forecast["wind"]
            }
        else:
            # Обновляем min/max температуры
            daily[date_str]["main"]["temp_min"] = min(
                daily[date_str]["main"]["temp_min"],
                forecast["main"]["temp"]
            )
            daily[date_str]["main"]["temp_max"] = max(
                daily[date_str]["main"]["temp_max"],
                forecast["main"]["temp"]
            )

            # Обновляем ощущаемую температуру (берем значение на полдень)
            time_str = dt_txt.split(" ")[1]
            if time_str == "12:00:00":
                daily[date_str]["main"]["temp"] = forecast["main"]["temp"]
                daily[date_str]["main"]["feels_like"] = forecast["main"]["feels_like"]
                daily[date_str]["weather"] = forecast["weather"]
                daily[date_str]["wind"] = forecast["wind"]

    # Сортируем по дате и возвращаем ВСЕ дни
    daily_forecasts = [daily[date] for date in sorted(daily.keys())]
    return daily_forecasts

# Поиск погоды по городу (inline режим)
@router.inline_query()
async def inline_weather(inline_query: types.InlineQuery):
    city = inline_query.query.strip()

    if not city:
        result = types.InlineQueryResultArticle(
            id='example',
            title='🌤️ Введите название города',
            description='Например: Москва, Минск, Астана',
            input_message_content=types.InputTextMessageContent(
                'Пример: @ваш_бот_username Москва'
            ),
        )
        await inline_query.answer([result], cache_time=1)
        return

    try:
        # Асинхронный запрос текущей погоды
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={token_weather}&lang=ru&units=metric'
            ) as response:
                if response.status != 200:
                    result = types.InlineQueryResultArticle(
                        id='error',
                        title='❌ Город не найден',
                        input_message_content=types.InputTextMessageContent(
                            f'❌ Город "{city}" не найден. Проверьте название.'
                        ),
                    )
                    await inline_query.answer([result], cache_time=1)
                    return

                json_response = await response.json()
                get_temp = json_response['main']['temp']
                weather_desc = json_response['weather'][0]['description']
                city_name = json_response['name']
                country = json_response['sys']['country']

                convert_to_celcius = math.ceil(get_temp)
                result_id = hashlib.md5(city.encode()).hexdigest()

                item = types.InlineQueryResultArticle(
                    id=result_id,
                    title=f'🌤️ {city_name}, {country}: {convert_to_celcius}°C',
                    description=weather_desc,
                    input_message_content=types.InputTextMessageContent(
                        f'🌍 *Погода в городе {city_name}, {country}*\n\n'
                        f'🌡️ Температура: *{convert_to_celcius}°C*\n'
                        f'📝 {weather_desc.capitalize()}',
                        parse_mode="Markdown"
                    ),
                )
                await inline_query.answer([item], cache_time=1)

    except Exception as e:
        result = types.InlineQueryResultArticle(
            id='error',
            title='❌ Ошибка',
            description='Произошла ошибка при получении данных',
            input_message_content=types.InputTextMessageContent(
                f'❌ Ошибка: {str(e)}'
            ),
        )
        await inline_query.answer([result], cache_time=1)


@router.message(Command("weather_help"))
async def get_weather_help(message: types.Message):
    help_text = (
        "🌤️ *Команды погоды:*\n\n"
        "🔹 *Inline режим:* Напишите `@имя_вашего_бота <город>`\n"
        "🔹 *Обычный режим:* Просто напишите название города\n\n"
        "📌 *Примеры:*\n"
        "• Москва\n"
        "• Санкт-Петербург\n"
        "• Лондон\n\n"
        "🌡️ Показывается прогноз на 5 дней"
    )
    await message.answer(help_text, parse_mode="Markdown")


# /weather_location - запрашиваем город
@router.message(Command("weather_location"))
async def cmd_weather_location(message: types.Message):
    await message.answer("🌍 Введите название города для прогноза погоды:")


# Обработчик текста (город)
@router.message(
    WeatherStates.forecast_weather,
    F.text,
    ~F.text.startswith("/"),
    ~F.text.in_([
        "🏠 Главное меню",
        "🦊 Показать лису",
        "ℹ️ Информация",
        "❓ Помощь",
        "🌤️ Погода",
        "📋 Задачи",
        "🎂 Дни рождения",
        "📝 Заметки",
        "🤖 AI Помощник",
        "💼 HR Рекрутер",
        "🌐 Переводчик"
    ])
)
@router.message(WeatherStates.forecast_weather, F.text)
async def show_weather_forecast(message: Message, state: FSMContext):
    """Обработчик ввода города для прогноза на 5 дней"""

    city = message.text.strip()

    # Проверяем, что это не команда
    if city.startswith('/'):
        await state.clear()
        return

    # Список кнопок, которые игнорируем
    button_texts = ["🏠 Главное меню", "🦊 Показать лису", "ℹ️ Информация", "❓ Помощь", "🌤️ Погода",
                    "📋 Задачи", "🎂 Дни рождения", "📝 Заметки", "🤖 AI Помощник", "💼 HR Рекрутер",
                    "🌐 Переводчик"]
    if city in button_texts:
        await state.clear()
        return

    # Отправляем уведомление
    wait_message = await message.answer(f"⏳ Получаю прогноз погоды для города *{city}* на 5 дней...",
                                        parse_mode="Markdown")

    try:
        # Получаем прогноз (асинхронно)
        forecasts = await get_forecast(city)
        logger.info(f"Получено {len(forecasts)} точек прогноза")

        daily_forecasts = aggregate_daily_forecast(forecasts)
        logger.info(f"Агрегировано {len(daily_forecasts)} дней")

        if not daily_forecasts:
            raise Exception("Не удалось получить данные о погоде")

        # Формируем сообщение с прогнозом
        forecast_message = f"🌍 *Прогноз погоды для {city} на 5 дней:*\n\n"

        for forecast in daily_forecasts[:5]:
            date = datetime.fromtimestamp(forecast["dt"]).strftime("%d.%m.%Y")
            temp_day = round(forecast["main"]["temp"])
            temp_min = round(forecast["main"]["temp_min"])
            temp_max = round(forecast["main"]["temp_max"])
            feels_like = round(forecast["main"]["feels_like"])
            humidity = forecast["main"]["humidity"]
            wind_speed = forecast["wind"]["speed"]
            description = forecast["weather"][0]["description"].capitalize()

            forecast_message += (
                f"📅 *{date}*\n"
                f"🌡️ Температура: {temp_day}°C (мин: {temp_min}°C, макс: {temp_max}°C)\n"
                f"🤔 Ощущается как: {feels_like}°C\n"
                f"📝 {description}\n"
                f"💧 Влажность: {humidity}%\n"
                f"💨 Ветер: {wind_speed} м/с\n\n"
            )

        # Удаляем сообщение ожидания
        try:
            await wait_message.delete()
        except:
            pass

        # Отправляем прогноз
        await message.answer(forecast_message, parse_mode="Markdown")

        # Очищаем состояние
        await state.clear()

        # Добавляем кнопки для продолжения
        await message.answer(
            "✅ Прогноз готов! Что дальше?",
            reply_markup=main_keyboard
        )

    except Exception as e:
        try:
            await wait_message.delete()
        except:
            pass
        error_msg = str(e)

        # Обработка специфических ошибок
        if "401" in error_msg:
            error_msg = "Неверный API ключ. Проверьте config.py"
        elif "404" in error_msg:
            error_msg = f"Город '{city}' не найден. Проверьте название"
        elif "429" in error_msg:
            error_msg = "Слишком много запросов. Попробуйте позже"

        await message.answer(
            f"❌ Ошибка при получении прогноза для города '{city}':\n\n"
            f"{error_msg}\n\n"
            f"💡 Проверьте правильность названия города и попробуйте снова.\n"
            f"Например: Москва, Санкт-Петербург, Лондон",
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "weather:current")
async def weather_current(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WeatherStates.current_weather)
    await callback.message.answer(
        "🌍 Введите город для текущей погоды:"
    )
    await callback.answer()


@router.callback_query(F.data == "weather:forecast")
async def weather_forecast(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Прогноз на 5 дней'"""
    await state.set_state(WeatherStates.forecast_weather)
    await callback.message.answer(
        "📅 Введите город для прогноза на 5 дней:"
    )
    await callback.answer()


@router.message(WeatherStates.current_weather, F.text)
async def show_current_weather(message: Message, state: FSMContext):
    """Обработчик ввода города для текущей погоды"""
    city = message.text.strip()

    # Проверяем, что это не команда
    if city.startswith('/'):
        await state.clear()
        return

    wait_message = await message.answer(
        f"⏳ Получаю текущую погоду для {city}..."
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://api.openweathermap.org/data/2.5/weather?"
                    f"q={city}&appid={token_weather}&lang=ru&units=metric"
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    error_message = error_data.get("message", "Неизвестная ошибка")
                    await wait_message.delete()
                    await message.answer(
                        f"❌ Ошибка: {error_message}\n\n"
                        f"Проверьте название города."
                    )
                    await state.clear()
                    return

                data = await response.json()

                temp = round(data["main"]["temp"])
                feels = round(data["main"]["feels_like"])
                humidity = data["main"]["humidity"]
                wind = data["wind"]["speed"]
                desc = data["weather"][0]["description"].capitalize()

                weather_text = (
                    f"🌍 Погода в городе {city}\n\n"
                    f"🌡 Температура: {temp}°C\n"
                    f"🤔 Ощущается как: {feels}°C\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind} м/с\n"
                    f"📝 {desc}"
                )

                await wait_message.delete()
                await message.answer(weather_text, reply_markup=main_keyboard)
                await state.clear()

    except Exception as e:
        try:
            await wait_message.delete()
        except:
            pass
        await message.answer(
            f"❌ Ошибка подключения:\n{str(e)}"
        )
        await state.clear()


@router.callback_query(F.data == "weather:change_city")
async def weather_change_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Сменить город'"""
    await state.set_state(WeatherStates.forecast_weather)
    await callback.message.answer(
        "🏙 Введите новый город:"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=main_keyboard
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return

    await state.clear()
    await message.answer(
        "✅ Действие отменено.",
        reply_markup=main_keyboard
    )