# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY crawler /app/crawler

RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install playwright
RUN playwright install chromium

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
