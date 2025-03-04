#!/bin/bash
set -e

echo ">>>>>>>> Starting Ollama server..."
ollama serve &

echo ">>>>>>>> Wait a few seconds for Ollama to spin up..."
sleep 5

echo ">>>>>>>> Pulling bge-m3 and qwen2.5 models..."
ollama pull bge-m3:latest
ollama pull qwen2.5:latest

# Keep container alive by waiting on the Ollama serve process
wait $!
