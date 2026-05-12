FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY model-hub/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY model-hub/ /app
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/shared
EXPOSE 8113
CMD ["uvicorn", "model_hub_service:app", "--host", "0.0.0.0", "--port", "8113"]
