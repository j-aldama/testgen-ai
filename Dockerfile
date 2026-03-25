FROM python:3.12-slim

LABEL maintainer="Juan Ignacio Aldama"
LABEL description="TestGen - AI-powered test case generator"

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e ".[dev]"

# Copy tests (for CI)
COPY tests/ ./tests/

# Expose web UI port
EXPOSE 8000

# Default command: run web UI
CMD ["testgen", "serve", "--port", "8000"]
