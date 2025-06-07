FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl unzip wget gnupg ca-certificates fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
    libgtk-3-0 libasound2 libxss1 libxcomposite1 libxrandr2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m playwright install chromium

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
