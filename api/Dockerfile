# FastAPI backend for the Patient Access & No-Show Automation Platform.
#
# Build context is the repo root (see docker-compose.yml); this Dockerfile is
# intentionally small — the API reads CSVs from data/ and models/ at startup,
# both of which are bind-mounted at runtime so the container can pick up
# freshly regenerated ETL output without a rebuild.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first so a code change doesn't invalidate the
# dependency layer.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Project code. Runtime data + models come via bind mounts in docker-compose
# so any change to data/ or models/ is picked up without rebuilding the image.
COPY api ./api
COPY etl ./etl
COPY models ./models
COPY sql ./sql

EXPOSE 8000

# Run as a non-root user; safer default even for a local demo image.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Simple container-level healthcheck: /health returns 200 with table counts.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
