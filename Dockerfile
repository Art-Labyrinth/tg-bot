# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Don't write .pyc files, don't buffer stdout — logs show up immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies as a separate layer — rebuilt only when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the app needs — explicitly, so nothing else (like .env, .venv
# or deploy/) can ever slip into the image, even if .dockerignore is misconfigured.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY start.sh ./
RUN chmod +x start.sh

# Entrypoint: apply migrations, then start the bot (see start.sh)
CMD ["./start.sh"]
