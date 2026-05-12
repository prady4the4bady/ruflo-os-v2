FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kryos_researcher.py .

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

EXPOSE 8120

CMD ["uvicorn", "kryos_researcher:app", "--host", "0.0.0.0", "--port", "8120"]
