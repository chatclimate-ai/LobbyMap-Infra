# Start from the NVIDIA CUDA runtime image for Ubuntu 24.04 (with CUDA 12.4.1).
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04


# Install essential system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-dev python3-venv \
    build-essential ninja-build zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment in /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the virtual environment
RUN /opt/venv/bin/pip install --upgrade pip

ENV TORCH_CUDA_ARCH_LIST="7.5"

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first (for layer caching)
COPY requirements.txt /app/

# Install dependencies from requirements.txt inside the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app

# Expose the port that gunicorn will listen on
EXPOSE 5000

# Launch gunicorn with uvicorn workers
CMD ["gunicorn", "docling_parser.api.server:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5000", "--timeout", "600"]
