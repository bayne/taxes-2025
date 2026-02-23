FROM python:3.14-slim AS base

WORKDIR /app

# Copy only what the server needs — no tests, no dev tooling
COPY models.py calculator.py server.py ./
COPY static/ static/

EXPOSE 8000

CMD ["python", "server.py", "8000"]
