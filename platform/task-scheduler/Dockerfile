FROM python:3.12-slim
RUN apt-get update && apt-get install -y sqlite3 && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY task-scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY task-scheduler/ /app
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/shared
CMD ["uvicorn", "scheduler_service:app", "--host", "0.0.0.0", "--port", "8110"]
