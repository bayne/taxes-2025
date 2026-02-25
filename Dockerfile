FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy only what the server needs — no tests, no dev tooling
COPY models.py calculator.py server.py ./
COPY static/ static/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "server.py", "8000"]
