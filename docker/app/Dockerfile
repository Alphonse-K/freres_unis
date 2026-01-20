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

# Create uploads folder and give permissions to appuser
RUN mkdir -p /app/uploads && \
    chown -R appuser:appuser /app/uploads

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/

RUN chown -R 999:999 /app/uploads

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
