# --- STAGE 1: THE CHEF (Build Stage) ---
FROM python:3.14-slim AS builder

ENV UV_SYSTEM_PYTHON=1 \
    PYTHONDONTWRITE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

# Copy project files for dependency installation
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- STAGE 2: THE MODEL (Final Stage) ---
FROM python:3.14-slim AS runner

ENV APP_HOME=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app

WORKDIR ${APP_HOME}

# Copy installed dependencies from builder
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the application code
COPY . .

EXPOSE 8000

# Healthcheck checking the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Use list format for easy SIGTERM handling
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
