FROM python:3.11-slim

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (must be done BEFORE chown)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create uploads/media/logs folders and give permissions to appuser.
# These get re-chowned at container start too (see entrypoint.py) since
# bind-mounting a host directory over these shadows this build-time chown
# whenever the host directory has different ownership (e.g. freshly
# auto-created by Docker as root).
RUN mkdir -p /app/uploads /app/media /app/logs && \
    chown -R appuser:appuser /app/uploads /app/media /app/logs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/
COPY docker/app/entrypoint.py /app/entrypoint.py

EXPOSE 8000

# Stays root here: entrypoint.py fixes bind-mount ownership as root, then
# drops to appuser and execs the real command (uvicorn, or celery worker/beat
# when docker-compose overrides CMD).
ENTRYPOINT ["python3", "/app/entrypoint.py"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
