# Use the official lightweight Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose the port expected by Cloud Run
EXPOSE 8080

# Start the app, using the $PORT provided by Cloud Run
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.enableCORS=false"]