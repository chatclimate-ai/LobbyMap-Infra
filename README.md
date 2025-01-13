# LobbyMap Infrastructure

The LobbyMap infrastructure consists of the following:
- The lobby map feedback API
- The Frontend

## Installation

- Clone the repository

```bash
git clone https://github.com/chatclimate-ai/LobbyMap-Infra.git
``` 

- Run the docker compose file

```bash 
docker-compose up
```


## Usage

1. Interact with the API using the following endpoints:
```bash
http://127.0.0.1:8000/feedback/
```

- GET /feedback: Get all feedbacks
- DELETE /feedback: Delete all feedbacks


2. Access the frontend using the following URL:
```bash
http://localhost:8501
```
