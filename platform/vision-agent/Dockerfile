FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vision_agent.py main.py ./
ENV PYTHONUNBUFFERED=1
EXPOSE 8091
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
