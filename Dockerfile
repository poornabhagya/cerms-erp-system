# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Multi-Stage Dockerfile (Python 3.12 / Django 5+ / Debian Bookworm)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/21_DOCKER_AND_LOCAL_DEVELOPMENT.md
# ==============================================================================

# ==============================================================================
# STAGE 1: Builder (Compilation & Dependency Resolution)
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install OS-level build tools, MariaDB/MySQL headers, image and PDF compilation libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    libjpeg-dev \
    libffi-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into /usr/local prefix
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/usr/local -r requirements.txt


# ==============================================================================
# STAGE 2: Runtime (Production & Staging Lean Image)
# ==============================================================================
FROM python:3.12-slim-bookworm

# Threading Restrictions: Prevent CPU Thrashing on AWS Graviton2 / Multi-core systems
ENV OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal runtime libraries (database driver, imaging, PDF fonts/rendering, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    libjpeg62-turbo \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    shared-mime-info \
    fontconfig \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python packages from builder stage
COPY --from=builder /usr/local /usr/local

# Copy application source code
COPY . /app

# Create unprivileged system user (cerms_user:1000) and configure directories
RUN useradd -u 1000 -U -s /bin/bash -m cerms_user && \
    mkdir -p /app/collected_static /app/media && \
    chown -R cerms_user:cerms_user /app

# Switch to non-root user for security hardening
USER cerms_user

# Expose internal Gunicorn application port
EXPOSE 8000

# Default entrypoint for WSGI HTTP server
CMD ["gunicorn", "cerms_project.wsgi:application", "--bind", "0.0.0.0:8000"]