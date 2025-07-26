# Use official Python image
FROM python:3.12-alpine

# RUN apt-get update && apt-get install -y \
#     python3 python3-dev \
#     libglib2.0-0 libglib2.0-dev libcairo2 libcairo2-dev \
#     libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev \
# && apt-get clean \
# && rm -rf /var/lib/apt/lists/*

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    ca-certificates \
    curl \
    bash

# Update CA certs
RUN update-ca-certificates

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
COPY .env .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8001

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
