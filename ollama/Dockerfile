FROM ollama/ollama:latest

# Ollama environment variable that forces it to bind 0.0.0.0:11434
ENV OLLAMA_ADDRESS=0.0.0.0:11434
ENV OLLAMA_KEEP_ALIVE=24h

WORKDIR /home

COPY pull-models.sh .
RUN chmod +x pull-models.sh

ENTRYPOINT ["/usr/bin/bash", "pull-models.sh"]
