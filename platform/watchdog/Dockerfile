FROM python:3.12-slim
RUN apt-get update && apt-get install -y sqlite3 && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY watchdog/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY watchdog/ /app
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV PYTHONPATH=/app:/app/shared
EXPOSE 8115
CMD ["uvicorn", "watchdog_service:app", "--host", "0.0.0.0", "--port", "8115"]
