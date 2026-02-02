# Stage 1: Base build stage
FROM python:3.13-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install BUILD dependencies (headers and compiler)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
COPY requirements.txt .

# Install to a local folder to make copying to Stage 2 cleaner
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Production stage
FROM python:3.13-slim

# Create user and directories
RUN useradd -m -r appuser && \
    mkdir /app && \
    chown -R appuser /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the compiled dependencies from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000