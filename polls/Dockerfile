# Stage 1: Build dependencies
FROM python:3.14-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .  # Assuming you have a requirements.txt; generate with pip freeze > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.14-slim

WORKDIR /app

# Install runtime dependencies (e.g., for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project code
COPY . .

# Collect static files (run this in docker-compose command)
RUN python manage.py collectstatic --noinput

# Use non-root user for security
RUN useradd -m appuser
USER appuser

# Expose port (Gunicorn will run on 8000)
EXPOSE 8000

# Run with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "fairPoll.wsgi:application"]
