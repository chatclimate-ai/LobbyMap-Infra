from typing import Optional, Dict, List
import requests
import json


    
def check_file_in_map(file_name: str, DATA_MAP: str) -> bool:
    existing_files = list_collection(DATA_MAP)
    for file in existing_files:
        if file["file_name"] == file_name:
            return True
    return False


def get_collections() -> List:
    try:
        response = requests.get("http://rag_api:8001/collections/read_files")
        response.raise_for_status()

        response_data = response.json()
        return response_data
    
    except:
        return {"files": []}


def save_collection(DATA_MAP: str, data: List[Dict]) -> None:
    with open(DATA_MAP, "w") as f:
        json.dump(data, f, indent=4)


def add_to_collection(DATA_MAP: str, data: Dict) -> None:
    existing_files = list_collection(DATA_MAP)
    existing_files.append(data)
    save_collection(DATA_MAP, existing_files)


def delete_prompt(PROMPT_MAP: str, prompt: str) -> None:
    prompts = list_prompts(PROMPT_MAP)
    prompts.remove(prompt)
    with open(PROMPT_MAP, "w") as f:
        json.dump(prompts, f, indent=4)

def list_collection(DATA_MAP: str) -> List:
    # file_name, author, Date, Region, size, url, num_chunks
    with open(DATA_MAP, "r") as f:
        existing_files = json.load(f)

    return existing_files

def list_prompts(PROMPT_MAP: str) -> List:
    with open(PROMPT_MAP, "r") as f:
        prompts = json.load(f)

    return prompts

def upload_call(
        file_path: str,
        author: str,
        date: Optional[str] = "",
        region: Optional[str] = "",
        size: Optional[int] = 0.0
        ) -> Dict:
    
    params = {
        "file_path": file_path,
        "author": author,
        "date": date,
        "region": region,
        "size": size
    }

    try:
        response = requests.get("http://rag_api:8001/collections/insert", params=params)
        response.raise_for_status()

        response_data = response.json()
        return response_data
    
    except:
        return {"num_chunks": 0}


def generator_call(
        query: str, 
        evidence: str,
        author: Optional[str] = None
        ) -> Dict:
    
    params = {
        "query": query,
        "evidence": evidence,
        "author": author
    }

    try:
        response = requests.get("http://rag_api:8001/generate/stance", params=params)
        response.raise_for_status()

        generator_response = response.json()
        return generator_response
    
    except:
        return {
            "stance": 0,
            "stance_text": "Failed to generate stance.",
            "stance_score": 0.0
        }

def retriever_call(
        query: str,
        author: Optional[str] = "",
        date: Optional[str] = "",
        region: Optional[str] = "",
        file_name: Optional[str] = "",
        top_k: Optional[int] = 5
        ) -> Dict:
    
    params = {
        "query": query,
        "author": author,
        "date": date,
        "region": region,
        "file_name": file_name,
        "top_k": top_k
    }

    try:
        response = requests.get("http://rag_api:8001/retrieve/filter", params=params)
        response.raise_for_status()

        response_data = response.json()
        return response_data
    
    except:
        return {"pdf_docs": {}}
