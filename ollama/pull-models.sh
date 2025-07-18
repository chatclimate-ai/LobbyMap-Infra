#!/bin/bash
set -e

echo ">>>>>>>> Starting Ollama server..."
ollama serve &

echo ">>>>>>>> Wait a few seconds for Ollama to spin up..."
sleep 5

echo ">>>>>>>> Pulling nomic-embed-text:latest and qwen3:1.7b models..."
ollama pull nomic-embed-text:latest
ollama pull qwen3:1.7b

# Keep container alive by waiting on the Ollama serve process
wait $!
