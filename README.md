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

## Features

- **Multilingual Support:** Handles documents in multiple languages using multilingual embedding models.
- **Flexible Parsing:** Supports both layout-aware and structure-agnostic parsing methods.
- **Dynamic Chunking:** Adapts chunk sizes based on layout structure and token limits.
- **Efficient Retrieval:** Uses vector databases for fast and scalable similarity search.

---

## Using the system in a VM in VastAI

#### 1. Create an account in VastAI and set up an instance:
- Create an account in VastAI, add you ssh key in the settings, and top up your account.
- Choose an instance with a docker template.
- Go to the `~/.ssh/config` on your local machine and add the following info (from the selected instance):
    ```
    Host lobbymap-vast
        HostName 136.38.166.236 # The IP of the instance
        Port 34873 # The port of the instance
        User root
        LocalForward 8000 localhost:8000 # The port of the Feedback API
        LocalForward 8001 localhost:8001 # The port of the RAG API
        LocalForward 8501 localhost:8501 # The port of the Frontend
        LocalForward 8002 localhost:8002 # The port of the PDF viewer
    ```
- To connect to your instance use the following command: `ssh lobbymap-vast`


#### 2. Add ssh key to Github to clone the code from the VM

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

#### 3. Installation

- Create a new directory:
    ```bash
    mkdir Projects
    cd Projects
    ```
- Clone the repository to the Virtual Machine (VM) using the following command:
   ```bash
   git clone https://github.com/chatclimate-ai/LobbyMap-Infra.git
   cd LobbyMap-Infra
   ```

#### 4. Add Nvidia-Docker support to your instance:

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

#### 5. Run the Docker Compose:
- Now you can run the docker compose with Nvidia support using the following command:
    ```bash
    docker-compose up --build
    ```
---

## Usage

#### 1. Query and Retrieve:
Use `Postman` or `Curl` to send requests to the Rag API with the query and filter parameters. For example:
```bash
curl -X 'GET' \
    'http://localhost:8001/retrieve/filter?query=energy transition %26 zero carbon technologies&top_k=2' \
    -H 'accept: application/json'
```
The server will return the most relevant chunks. For other Endpoints, refer to the `http://localhost:8001/docs`.


#### 2. Frontend Interface:
- The interface will be available at `http://localhost:8501`.
- To upload a PDF file, click on the `Upload PDF` button and select the file. The system will prompt you to enter the author, region, and date of the document. The `author` field is required, while the `region` and `date` fields are optional.
- All files available in the system will be displayed in the `Files` section. 
- Click on the `View` button to see the content of the file. The file will open in a new browser tab at `http://localhost:8002/file.pdf`.
   
#### 3. Feedback API:
The Feedback API will be available at `http://localhost:8000`. To get all collected feedback from the `MongoDB` database, use the following command:
```bash
curl -X 'GET' \
    'http://127.0.0.1:8000/feedback/' \
    -H 'accept: application/json'
```

---

## Development

#### 1. Add New Models:
To add new models, update the `ollama/pull-models.sh` file with the new model names. Then, rebuild the Docker containers using the following command:
```bash
docker-compose up --build
```

#### 2. Update the RAG Vector Database:
- To add a new document to the RAG vector database, use the Frontend interface or the RAG API with the following command:
```bash
curl -X 'GET' \
    'http://localhost:8001/insert' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "file_path": "/path/to/file.pdf", # Required
    "author": "Author", # Required
    "region": "Region",
    "date": "Date"
    }'
```

- To delete a document from the RAG vector database, use the following command:
```bash
curl -X 'GET' \ 
    'http://localhost:8001/delete' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
    "file_name": "file.pdf" # Required
    }'
```


