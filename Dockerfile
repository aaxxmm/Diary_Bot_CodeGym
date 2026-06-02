FROM python:3.14-slim

# Устанавливаем ffmpeg - ЭТО КЛЮЧЕВОЙ МОМЕНТ!
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Проверяем установку ffmpeg
RUN ffmpeg -version || echo "ffmpeg not found"
# Проверяем, что main.py существует
RUN ls -la && test -f main.py && echo "main.py found" || echo "main.py NOT found"
# Отладочная информация
RUN echo "=== Файлы в /app ===" && ls -la /app
RUN echo "=== Поиск main.py ===" && find /app -name "main.py" -type f
# Запускаем бота
CMD ["python", "./main.py"]














# Запускаем бота
CMD ["python", "main.py"]