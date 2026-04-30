FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy local modules and application code
COPY flockbasedlock/ ./flockbasedlock/
COPY selfdroid/ ./selfdroid/

# Expose Flask port
EXPOSE 5000

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "selfdroid:app"]
