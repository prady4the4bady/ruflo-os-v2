# Ahnis — AI Memory Service (formerly mempalace-Aya-fork)
# Prady OS ai-core/ahnis service
FROM python:3.11-slim

# Non-root user for security
RUN groupadd -r ahnis && useradd -r -g ahnis ahnis

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# Mount point for the mempalace-Aya-fork submodule (compositor/ahnis)
VOLUME ["/app/compositor/ahnis"]

USER ahnis
EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8091/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8091", "--log-level", "info"]
