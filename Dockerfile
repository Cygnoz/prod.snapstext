FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libzbar0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create virtual environment and set permissions
RUN python -m venv /opt/venv && \
    chown -R appuser:appuser /opt/venv

# Set permissions for the working directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Install Python dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run with Gunicorn
CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]