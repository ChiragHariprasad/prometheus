FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' appuser

WORKDIR /app

COPY requirements-core.txt .
RUN pip install --no-cache-dir --default-timeout=120 --prefer-binary -r requirements-core.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools", "--proxy-headers", "--forwarded-allow-ips", "*"]
