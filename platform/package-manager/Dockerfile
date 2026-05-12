FROM python:3.12-slim

WORKDIR /app

COPY package-manager/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY package-manager/package_manager_service.py ./
COPY package-manager/catalog/ ./catalog/
COPY shared /app/shared

ENV DATA_DIR=/data
ENV CATALOG_DIR=/app/catalog
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/shared

EXPOSE 8116

CMD ["uvicorn", "package_manager_service:app", "--host", "0.0.0.0", "--port", "8116"]
