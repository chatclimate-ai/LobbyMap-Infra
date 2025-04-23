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

ENV TORCH_CUDA_ARCH_LIST="7.5"

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first (for layer caching)
COPY requirements.txt /app/

# Install dependencies from requirements.txt inside the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . /app


WORKDIR /app/rag
# 6. Expose the port your FastAPI (or other framework) will listen on

EXPOSE 8001

# 7. Define the command to run the app
CMD ["gunicorn", "backend.server:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001"]
