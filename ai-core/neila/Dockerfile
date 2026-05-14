# Neila — Desktop Agent Runtime (formerly ouroboros-desktop)
# Prady OS ai-core/neila service
FROM python:3.11-slim

# Non-root user for security
RUN groupadd -r neila && useradd -r -g neila neila

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# Mount point for the ouroboros-desktop submodule (compositor/neila)
VOLUME ["/app/compositor/neila"]

USER neila
EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090", "--log-level", "info"]
