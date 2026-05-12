FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr xdotool libx11-dev scrot \
    libxtst-dev libpng-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY platform/computer-use/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy just the service files so they live at /app (not /app/platform/...)
COPY platform/computer-use/computer_use_service.py /app/
COPY platform/computer-use/task_loop.py /app/
# Shared auth module for services that might import it at runtime
COPY platform/shared /app/shared

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/shared

EXPOSE 8106

CMD ["uvicorn", "computer_use_service:app", "--host", "0.0.0.0", "--port", "8106"]
