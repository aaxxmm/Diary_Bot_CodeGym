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

# Запускаем бота
CMD ["python", "main.py"]














# Запускаем бота
CMD ["python", "main.py"]