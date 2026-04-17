# -------- Stage 1: Build --------
FROM python:3.14-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps \
    --wheel-dir /app/wheels \
    -r requirements.txt


# -------- Stage 2: Final --------
FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# system deps (runtime only)
RUN apt-get update \
 && apt-get install -y --no-install-recommends gettext \
 && rm -rf /var/lib/apt/lists/*

# create non-root user
RUN addgroup --system django \
 && adduser --system --ingroup django --home /home/django django

# install python deps
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# copy project
COPY . .

# Compile translations
RUN python manage.py compilemessages

# prepare directories + permissions
RUN mkdir -p /app/static /app/media /app/data \
 && chown -R django:django /app

USER django

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "condorcet_backend.wsgi:application"]
