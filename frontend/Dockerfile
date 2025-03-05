FROM python:3.12-slim

# 1. Set working directory
WORKDIR /app

# 2. Copy only requirements.txt first for caching
COPY requirements.txt /app/

# 3. Install dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your application code
COPY . /app

# 5. Set the working directory to where the Streamlit app resides
WORKDIR /app/frontend

# 5. Expose the port Streamlit will listen on
EXPOSE 8501

# 6. Define the command to run the Streamlit app
CMD ["streamlit", "run", "ui.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.maxUploadSize=20"]
