FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# App source.
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Run migrations, seed only if empty, then serve. Binds Railway's $PORT (falls back to 8000 locally).
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
