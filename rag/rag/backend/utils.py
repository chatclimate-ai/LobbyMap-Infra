from typing import List, Dict, Optional
from backend.templates import read_prompt_template, read_tool
from tenacity import retry, wait_fixed, stop_after_attempt
from ollama import Client
import jinja2
from sentence_transformers import CrossEncoder
from FlagEmbedding import FlagReranker


def rank(
        model_name: str, 
        query: str, 
        evidences: List[Dict]
        ) -> List:
    """
    A function to rank the evidences based on the stance prediction.
    :param model_name: The name of the model to use
    :param query: The query to search for
    :param evidences: A list of evidences to rank
    :param confidence_scores: A list of confidence scores for each evidence
    :return: A list of ranked evidences
    """
    evidence_contents = [chunk.get("content") for chunk in evidences]

    if model_name.startswith("BAAI"):
        rank_scores = bge_rerank(model_name, query, evidence_contents)
    
    else:
        rank_scores = cross_encoder_rerank(model_name, query, evidence_contents)
    
    return rank_scores



def bge_rerank(model_name:str, query: str, evidence_contents: List[str]) -> List:
    """
    A function to rerank the documents using the BGE model.
    :param query: The query to search for
    :param documents: A list of documents to rerank
    :return: A list of reranked documents
    """

    model = FlagReranker(
        model_name,
        use_fp16=False,
        devices=["cuda:0"],
        )

    sentence_pairs = [[query, evidence] for evidence in evidence_contents]
    return model.compute_score(sentence_pairs, normalize=True)


def cross_encoder_rerank(model_name:str, query: str, evidence_contents: List[str]) -> List:
    """"
    Rerank the documents using the Jina Reranker.
    :param query: The query to rerank the documents against.
    :param documents: A list of documents to rerank.
    """
    model = CrossEncoder(
        model_name,
        automodel_args={"torch_dtype": "auto"},
        trust_remote_code=True,
    )
   
    sentence_pairs = [[query, evidence] for evidence in evidence_contents]
    return model.predict(sentence_pairs, convert_to_tensor=True).tolist()




# "jinaai/jina-reranker-v2-base-multilingual", max_length=1024
# "mixedbread-ai/mxbai-rerank-large-v1", max_length=512, english only
# "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512
# "BAAI/bge-reranker-v2-m3", max_length=8192
# "BAAI/bge-reranker-v2-gemma", max_length=8192





PROMPT_TEMPLATE: str = read_prompt_template("stance_prompt")
TOOL: dict = read_tool("stance_schema")


def generate_stance_prompt(
        evidence: str,
        query: str,
        author: Optional[str] = None
        ) -> str:
    
    environment = jinja2.Environment()
    _template = environment.from_string(PROMPT_TEMPLATE)
    
    if author is not None:
        author = f"""Here is the company in question:\n{author}"""
    
    else:
        author = ""
    prompt = _template.render(
        evidence=evidence,
        query=query,
        author= author
    )
    return prompt




@retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
def generate(
    model_name:str, 
    evidence: str,
    query: str, 
    author: Optional[str] = None,
    ):
    try:
        # Generate prompt
        prompt = generate_stance_prompt(
            evidence, 
            query, 
            author
        )

        # Initialize Ollama client
        client = Client(host="http://ollama:11434")

        # Get response from the model
        response = client.chat(
            model= model_name,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ],
            tools = [TOOL],
            # format= "json",
            options={"temperature": 0}
        )
        # Get stance scores and reasons
        arguments = response.get("message", {}).get("tool_calls", [])[0].get("function", {}).get("arguments", {}).get("evidence_scores", [])[0]


        return {
            "score": arguments.get("score", 0),
            "stance_text": arguments.get("reason", "Failed to generate stance.")
        }

    except:
        return {
            "score": 0,
            "stance_text": "Failed to generate stance."
        }    
