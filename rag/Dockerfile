FROM python:3.12-slim

# 1. Set working directory
WORKDIR /app

# 2. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Copy only requirements.txt first for caching
COPY requirements.txt /app/

# 4. Install dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# 4.1 Install PyTorch and TorchVision from the specific index URL
RUN pip install --no-cache-dir \
    torch \
    torchvision \
    --index-url https://download.pytorch.org/whl/cu121


# 5. Copy the rest of your application code
COPY . /app

WORKDIR /app/rag
# 6. Expose the port your FastAPI (or other framework) will listen on
EXPOSE 8001

# 7. Define the command to run the app
CMD ["gunicorn", "-w", "10", "-k", "uvicorn.workers.UvicornWorker", "backend.server:app", "--bind", "0.0.0.0:8001"]
