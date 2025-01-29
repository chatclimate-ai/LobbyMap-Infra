#!/bin/bash
set -e

# Start Ollama server in the background, binding to all interfaces
echo ">>>>>>>> Starting Ollama and pulling models..."
ollama serve &

# Wait a few seconds for Ollama to spin up
sleep 5

# Pull the models you need
echo ">>>>>>>> Pulling bgme-m3 and qwen2.5 models..."
ollama pull bge-m3:latest
ollama pull qwen2.5:latest

# Keep container alive by waiting on the ollama serve process
wait $!
