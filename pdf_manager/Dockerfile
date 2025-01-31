FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy PDFs from the host machine into /app/data/documents
COPY ../data/documents /app/data/documents

RUN chmod -R 775 /app/data/documents
CMD ["sh", "-c", "true"]
