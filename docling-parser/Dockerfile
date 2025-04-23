FROM python:3.12-slim


# 1. Set working directory
WORKDIR /app

# 2. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment in /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the virtual environment
RUN /opt/venv/bin/pip install --upgrade pip

# ENV TORCH_CUDA_ARCH_LIST="7.5"

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first (for layer caching)
COPY requirements.txt /app/

# Install dependencies from requirements.txt inside the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app

# Expose the port that gunicorn will listen on
EXPOSE 8888

# Launch gunicorn with uvicorn workers
CMD ["gunicorn", "docling_parser.api.server:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8888", "--timeout", "600"]
