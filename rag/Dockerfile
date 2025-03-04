# Start from the NVIDIA CUDA runtime image for Ubuntu 24.04 (with CUDA 12.6.1).
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

# Install essential system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    build-essential \
    ninja-build \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment in /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the virtual environment
RUN pip install --upgrade pip

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first (for layer caching)
COPY requirements.txt /app/

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app

# Switch to the rag folder
WORKDIR /app/rag

# Expose the port that gunicorn will listen on
EXPOSE 8001

# Launch gunicorn with uvicorn workers
CMD ["gunicorn", "backend.server:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001", "--timeout", "300"]
