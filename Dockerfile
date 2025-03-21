FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    # Set a default (empty) OpenAI API key to prevent crashes
    OPENAI_API_KEY=""

# Expose the port
EXPOSE 8000

# Create startup script to handle missing dependencies gracefully
RUN echo '#!/bin/bash\n\
echo "Ensuring all dependencies are installed..."\n\
pip install --no-cache-dir -r requirements.txt\n\
echo "Starting application..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Start the application with the startup script
CMD ["/app/start.sh"] 