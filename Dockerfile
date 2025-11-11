# === Stage 1: Build ===
FROM python:3.11-slim AS builder

# Set workdir
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends libopus0 libopus-dev && rm -rf /var/lib/apt/lists/*


# Install poetry or pip depending on your setup
COPY pyproject.toml poetry.lock* requirements.txt* ./

# Prefer poetry if exists

# Install dependencies in a virtual env folder
RUN pip install --no-cache-dir -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.11-slim

# Workdir
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libopus0 && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project files
COPY . .

# Expose FastAPI port
EXPOSE 8080

# Start server with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
