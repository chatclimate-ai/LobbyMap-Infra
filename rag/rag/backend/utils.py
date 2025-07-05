from typing import List, Dict, Optional
from backend.templates import read_prompt_template, read_tool
from ollama import Client
import jinja2
from FlagEmbedding import FlagReranker
import json
import re


def init_reranker(reranker_name: str):
    model = FlagReranker(
        reranker_name,
        use_fp16=True
    )
    return  model

def rank(
        model,
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
    sentence_pairs = [[query, evidence] for evidence in evidence_contents]

    rank_scores = model.compute_score(sentence_pairs, normalize=True)
    return rank_scores









PROMPT_TEMPLATE: str = read_prompt_template("stance_prompt")
TOOL: dict = read_tool("stance_schema")
CLIENT = Client(host="http://ollama:11434")

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

def parse_json(content:str):
    json_blocks = re.findall(r"\{[\s\S]+?\}", content)
    json_obj = None
    for block in reversed(json_blocks):
        try:
            # PATCH: Fix common truncation issues (missing ]}})
            if '"evidence_scores": [' in block and not block.strip().endswith("]}}"):
                block = block.strip() + "]}}"

            parsed = json.loads(block)
            if "arguments" in parsed and "evidence_scores" in parsed["arguments"]:
                json_obj = parsed
                break
        except json.JSONDecodeError as err:
            continue
    
    if json_obj is None:
        raise ValueError("No valid JSON block found in the output.")

    # Extract score and reason
    score_str =  " " + str(json_obj["arguments"]["evidence_scores"][0]["score"])
    reason = json_obj["arguments"]["evidence_scores"][0]["reason"]

    return {
        "score": int(score_str),
        "stance_text": reason
    }



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

        # Get response from the model
        response = CLIENT.chat(
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
        print("Using tool call parsing")
        return {
            "score": arguments.get("score", 0),
            "stance_text": arguments.get("reason", "Failed to generate stance.")
        }

    except IndexError as e:
        # Fallback to parsing JSON from content
        content = response.get("message", {}).get("content", "")
        parsed_result = parse_json(content)

        print("Using content parsing")
        return parsed_result



    except Exception as e:
        print(f"Error generating stance: {e}")
        return {
            "score": 0,
            "stance_text": "Failed to generate stance."
        }    
