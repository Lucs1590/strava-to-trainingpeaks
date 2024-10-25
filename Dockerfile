FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt /app/requirements.txt

COPY src /app/src  

RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /app /app

RUN useradd -m -d /app appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["/app/venv/bin/python", "src/main.py"]
