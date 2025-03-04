#!/bin/bash
set -e

echo ">>>>>>>> Starting Ollama server..."
ollama serve &

echo ">>>>>>>> Wait a few seconds for Ollama to spin up..."
sleep 5

echo ">>>>>>>> Pulling bge-m3 and qwen2.5 models..."
ollama pull bge-m3:latest
ollama pull qwen2.5:latest

echo ">>>>>>>> Warming up bge-m3..."
curl -s -X POST -H "Content-Type: application/json" \
     -d '{"prompt":"Just load bge-m3 so it’s ready"}' \
     http://127.0.0.1:11434/v1/completions?model=bge-m3

echo ">>>>>>>> Warming up qwen2.5..."
curl -s -X POST -H "Content-Type: application/json" \
     -d '{"prompt":"Just load qwen2.5 so it’s ready"}' \
     http://127.0.0.1:11434/v1/completions?model=qwen2.5

# Keep container alive by waiting on the Ollama serve process
wait $!
