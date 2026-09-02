FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend ./backend
COPY infra/postgres/init ./infra/postgres/init

ENV PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1

CMD ["/app/.venv/bin/python", "-m", "app.runtime", "notes-worker"]
