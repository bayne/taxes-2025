FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync

COPY . .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "server.py", "8000"]
