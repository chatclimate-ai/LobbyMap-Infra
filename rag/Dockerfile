# Start from the NVIDIA CUDA runtime image for Ubuntu 24.04 (with CUDA 12.6.1).
FROM nvidia/cuda:12.6.1-devel-ubuntu24.04

# Install essential system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3.12-venv \
    build-essential ninja-build zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment in /opt/venv
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the virtual environment
RUN /opt/venv/bin/pip install --upgrade pip

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first (for layer caching)
COPY requirements.txt /app/

# Install dependencies from requirements.txt inside the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Install PyTorch/TorchVision with CUDA 12.6 support
RUN /opt/venv/bin/pip install --no-cache-dir \
    torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126

# Copy the rest of your application code
COPY . /app

# Switch to the rag folder
WORKDIR /app/rag

# Expose the port that gunicorn will listen on
EXPOSE 8001

# Launch gunicorn with uvicorn workers
CMD ["gunicorn", "backend.server:app", "-w", "3", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001", "--timeout", "600"]