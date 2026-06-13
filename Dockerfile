# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Don't write .pyc files, don't buffer stdout — logs show up immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies as a separate layer — rebuilt only when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Run the package: python -m app
CMD ["python", "-m", "app"]
