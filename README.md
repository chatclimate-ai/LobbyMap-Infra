# Lobbymap
The main repository for the InfluenceMap LobbyMap Platform. This repository contains the implementation of a Retrieval-Augmented Generation (RAG) system designed for multilingual retrieval tasks. The system processes large document datasets, splits them into meaningful chunks, and retrieves the most relevant chunks to answer user queries using semantic similarity techniques.

---

## Overview

The RAG system combines state-of-the-art parsing, chunking, embedding, and retrieval methods to efficiently handle multilingual documents. The key components include:

1. **Parsing:** Converts documents into plain text while optionally preserving layout.
2. **Chunking:** Splits text into smaller chunks suitable for vectorization and retrieval.
3. **Embedding:** Converts chunks into dense vector representations using multilingual models.
4. **Retrieval:** Retrieves the most relevant chunks using a vector database and ranks them based on semantic similarity.

---

## Project Structure
.
├── README.md
├── config.yaml
├── data
│   ├── documents
│   └── weaviate_data
├── docker-compose.yml
├── feedback-tool
│   ├── Dockerfile
│   ├── feedback-tool
│   │   ├── __init__.py
│   │   └── api
│   │       ├── __init__.py
│   │       ├── schema.py
│   │       └── server.py
│   ├── poetry.lock
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── tests
├── frontend
│   ├── Dockerfile
│   ├── README.md
│   ├── frontend
│   │   ├── __init__.py
│   │   ├── ui.py
│   │   └── utils.py
│   ├── images
│   ├── poetry.lock
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── tests
├── ollama
│   ├── Dockerfile
│   └── pull-models.sh
├── pdf_manager
│   └── Dockerfile
└── rag
    ├── Dockerfile
    ├── README.md
    ├── poetry.lock
    ├── pyproject.toml
    ├── rag
    │   ├── __init__.py
    │   ├── backend
    │   │   ├── __init__.py
    │   │   ├── server.py
    │   │   ├── templates
    │   │   │   ├── stance_prompt.jinja
    │   │   │   └── stance_schema.json
    │   │   └── utils.py
    │   └── lobbymap_search
    │       ├── __init__.py
    │       └── etl
    │           ├── __init__.py
    │           ├── chunker.py
    │           ├── parser.py
    │           ├── parsers
    │           │   ├── docling_parse.py
    │           │   ├── pymupdf_parse.py
    │           │   └── schemas.py
    │           ├── pipeline.py
    │           └── schemas.py
    ├── requirements.txt
    └── tests

---

## Features

- **Multilingual Support:** Handles documents in multiple languages using multilingual embedding models.
- **Flexible Parsing:** Supports both layout-aware and structure-agnostic parsing methods.
- **Dynamic Chunking:** Adapts chunk sizes based on layout structure and token limits.
- **Efficient Retrieval:** Uses vector databases for fast and scalable similarity search.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/chatclimate-ai/LobbyMap-Infra.git
   cd LobbyMap-Infra
   ```
2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

## Using the project repo in a VM in VastAI

- Create an account in VastAI, add you ssh key in the settings, and top up your account.
- Choose an instance and then select it with preferably a docker template.
- Go to the `~/.ssh/config` and add the following info that you will get from your instance:
    ```
    Host lobbymap-vast
      HostName 136.38.166.236
      Port 34873
      User root
      LocalForward 8080 localhost:8080
      LocalForward 8000 localhost:8000
    ```
- To connect to your instance use the following command: `ssh lobbymap-vast`

### Add Nvidia-Docker support to your instance:

- Install Nvidia-Docker:
    ```bash
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
  ```

- After installation, configure the Docker daemon to recognize the NVIDIA runtime:
    ```bash
    sudo nvidia-ctk runtime configure --runtime=docker
    ```

- Finally, restart the Docker service to apply the changes:
    ```bash
    sudo systemctl restart docker
    ```

- Test the configuration, After making these changes, test the setup by running a simple CUDA container:
    ```bash
    sudo docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
    ```
- Install the docker compose app:
    ```bash
    apt  install docker-compose
    ```
- Now you can run the docker compose with Nvidia support using the following command:
    ```bash
    docker-compose up --build
    ```
## Add ssh key to Github to clone the code from the VM

- Generate a new ssh key in the VM using the following command:
    ```bash
    ssh-keygen -t ed25519 -C "your_email@example.com"
    ```
- Start the SSH agent
    ```bash
    eval "$(ssh-agent -s)"
    ```
- Add the SSH key to the SSH agent
    ```bash
    ssh-add ~/.ssh/id_ed25519
    ```
- Copy the SSH key to the clipboard
    ```bash
    cat ~/.ssh/id_ed25519.pub
    ```
- Add the key to Github, now you can clone the repo using the SSH key.

## Usage

1. **Configuration**:
    In the `config.yaml` file, set the parameters of the pipeline, including the parsing, chunking, and retrieval methods. The default configuration is provided in the `config.yaml` file.

2. **Docker Setup**:
    Launch the Docker Compose setup from the root directory:
    ```bash
    docker compose up -d --build
    ```


3. **Query and Retrieve:**
   Use `Postman` or `Curl` to send requests to the server with the query and filter parameters:
    ```bash
    curl -X 'GET' \
      'http://rag_api:8001/retrieve/filter?query=energy transition %26 zero carbon technologies&top_k=2' \
      -H 'accept: application/json'
    ```
    The server will return the most relevant chunks. For other Endpoints, refer to the `http://rag_api:8001/docs`.


4. **Frontend Interface:**
   The interface will be available at `http://frontend:8501`.
   
---
