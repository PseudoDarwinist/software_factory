FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY frontend/ ./frontend/

# Build Mission Control frontend (Vite) inside the image so files exist
# 1) Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2) Copy mission-control sources and build to ../mission-control-dist as per vite.config.ts
COPY mission-control/ ./mission-control/
RUN npm ci --prefix mission-control \
    && npm run build --prefix mission-control

# Create directories for logs and instance data
RUN mkdir -p /app/logs /app/instance

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/health || exit 1

# Run the application
CMD ["python", "-m", "src.app"]