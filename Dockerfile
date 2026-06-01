FROM python:3.14-slim

# Обновляем менеджер пакетов и устанавливаем FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем папку для данных
RUN mkdir -p /app/data

# Запускаем бота
CMD ["python", "main.py"]














# Запускаем бота
CMD ["python", "main.py"]