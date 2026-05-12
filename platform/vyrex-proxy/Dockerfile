FROM python:3.12-slim

WORKDIR /app

COPY vyrex-proxy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vyrex-proxy/vyrex_proxy.py .
COPY shared /app/shared

ENV PYTHONPATH=/app:/app/shared

EXPOSE 8105
CMD ["uvicorn", "vyrex_proxy:app", "--host", "0.0.0.0", "--port", "8105"]
