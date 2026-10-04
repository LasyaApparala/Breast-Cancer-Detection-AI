FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for ChromaDB persistence
RUN mkdir -p /app/chroma_db

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8003/health')"

# Run the service
CMD ["uvicorn", "rag_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
