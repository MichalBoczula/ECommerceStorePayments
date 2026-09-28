# syntax=docker/dockerfile:1
FROM python:3.14.7-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-editable --no-install-project --python /usr/local/bin/python

COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python \
    && uv pip list --python /app/.venv/bin/python | grep -q '^ecommerce-store-payments '

FROM python:3.14.7-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=build --chown=10001:10001 /app/.venv /app/.venv
USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
    CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8080/health/live', timeout=2).status == 200"

CMD ["uvicorn", "ecommerce_store_payments.main:app", "--host", "0.0.0.0", "--port", "8080"]
