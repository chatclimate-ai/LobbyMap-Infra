FROM python:3.12-slim

# 1. Set working directory
WORKDIR /app

# 2. Copy only requirements.txt first for caching
COPY requirements.txt /app/

# 3. Install dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your application code
COPY . /app

# 5. Expose the port your FastAPI (or other framework) will listen on
EXPOSE 8000

# 6. Define the command to run the app
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "feedback-tool.api.server:app", "--bind", "0.0.0.0:8000"]
