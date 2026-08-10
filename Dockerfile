# Python FastAPI backend
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY python_backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt Pillow

COPY python_backend/ ./
COPY public ./public
COPY migrations ./migrations

RUN mkdir -p uploads

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
