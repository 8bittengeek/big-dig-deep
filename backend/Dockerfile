# Start from the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /app

# Copy only requirements file first 
COPY backend/requirements.txt .

# Install Python deps, including playwright
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install warcio httpx && \
    python -m playwright install

# Copy code after installing deps
COPY backend/ backend/
COPY crawler/ crawler/

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
