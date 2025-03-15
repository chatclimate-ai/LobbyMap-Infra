from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rag.lobbymap_search.etl.pipeline import PdfDocumentPipeline
import weaviate.classes as wvc
from weaviate.classes.aggregate import GroupByAggregate
from weaviate.classes.query import MetadataQuery
from contextlib import asynccontextmanager
from typing import Dict, Optional, List, Union
from rag.backend.utils import rank, generate
from rag.lobbymap_search.etl.schemas import Chunk
import yaml

description = """
LobbyMap Search API

This API facilitates the following functionality:
- Managing a collection of PDF documents stored in a vector database.
- Running semantic and filtered queries to retrieve evidence on corporate climate lobbying.
- Ranking and scoring retrieved evidence for relevance and stance generation.
- Deleting or managing collections in the vector database.

Features include:
- Support for multilingual documents.
- Advanced ranking and stance generation using LLMs.
- Integration with Weaviate for vector storage and search.
"""

config_path = "/app/config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

COLLECTION_NAME = config["Weaviate_options"]["collection_name"]
RERAKER = config["Weaviate_options"]["reranker"]
GENERATOR = config["Weaviate_options"]["generator"]
VECTORIZER = config["Weaviate_options"]["vectorizer"]

FILE_SYSTEM = config["Backend"]["file_system"]
FILE_SYSTEM_SERVER = config["Backend"]["file_system_server"]

PARSER = config["parser_options"]["parser"]
SAVE_PARSED_CONTENT = config["parser_options"]["save_parsed_content"]
MD_OUTPUT_DIR = FILE_SYSTEM + "/" + config["parser_options"]["output_dir"]
PARSER_OPTIONS = config[config["parser_options"]["parser_options"]]

CHUNKING_METHOD = config["Chunker"]["chunking_method"]
CHUNKING_OPTIONS = config[config["Chunker"]["chunking_options"]]


pipeline = PdfDocumentPipeline(
    collection_name=COLLECTION_NAME,
    parser=PARSER,
    parser_options=PARSER_OPTIONS,
    save_locally=SAVE_PARSED_CONTENT,
    save_dir=MD_OUTPUT_DIR,
    chunking_method=CHUNKING_METHOD,
    chunking_options=CHUNKING_OPTIONS,
    vectorizer=VECTORIZER
)

ARTIFACTS = {
    "parser": {
        "model_name": PARSER,
        "options": PARSER_OPTIONS
    },
    "chunker": {
        "chunking_method": CHUNKING_METHOD,
        "options": CHUNKING_OPTIONS
    },
    "rag_components": {
        "collection_name": COLLECTION_NAME,
        "vectorizer_model_name": VECTORIZER,
        "reranker_model_name": RERAKER,
        "generator_model_name": GENERATOR
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to Weaviate
    pipeline.connect_to_weaviate()
    yield
    # Shutdown: close the Weaviate connection
    pipeline.close()


app = FastAPI(
    lifespan=lifespan,
    title="LobbyMap Search API",
    description=description,
    summary= "The LobbyMap Search API provides endpoints for managing and querying a vector database of PDF documents related to corporate climate lobbying. It enables efficient evidence retrieval, filtering, and ranking across multilingual datasets. The API also integrates with LLMs to generate insights and stances based on retrieved evidence.",


    )
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to the origin of your frontend if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/collections/count")
async def get_collections_count() -> Dict:
    """
    Get the total count of PDF documents in the collection.

    Returns:
        dict: A dictionary containing the total count of documents in the vector database collection.

    Raises:
        HTTPException: If the database query fails.
    """
    try:
        pdf_docs = pipeline.client.collections.get(COLLECTION_NAME)
        response = pdf_docs.aggregate.over_all(total_count=True)

        return {
            "pdf_docs_count": [
                {
                    "total_count": response.total_count,
                }
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/unique")
async def get_unique_values(attribute: str) -> Dict:
    """
    Get the unique values of a specified attribute within the collection.

    Parameters:
        attribute (str): The name of the attribute to retrieve unique values for.

    Returns:
        dict: A dictionary with the unique values of the specified attribute and their counts.

    Raises:
        HTTPException: If the database query fails.
    """
    try:
        # Get the collection
        collection = pipeline.client.collections.get(COLLECTION_NAME)

        # Perform an aggregate query to get unique authors
        response = collection.aggregate.over_all(
            group_by=GroupByAggregate(prop=attribute, limit=1000),
            total_count=True
        )

        # Extract and format the response
        result = [
            {
                attribute: group.grouped_by.value,
                "total_count": group.total_count
            }
            for group in response.groups
        ]

        return {attribute: result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/count_unique")
async def count_unique_values(attribute: str) -> Dict:
    """
    Get the count of unique values of a specified attribute.

    Parameters:
        attribute (str): The attribute to count unique values for.

    Returns:
        dict: A dictionary containing the count of unique values.

    Raises:
        HTTPException: If the query fails.
    """
    try:
        # Get the collection
        collection = pipeline.client.collections.get(COLLECTION_NAME)

        response = collection.aggregate.over_all(
            group_by=GroupByAggregate(prop=attribute, limit=1000),
            total_count=False
        )
        result = len(response.groups)
        return {attribute: result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/collections/delete/file")
async def delete_document_from_weaviate(file_name: str) -> Dict:
    """
    Delete a specific document from the vector database.

    Parameters:
        file_name (str): The name of the file to delete.

    Returns:
        dict: A message indicating success or failure of the deletion.

    Raises:
        HTTPException: If the file is not found or deletion fails.
    """
    try:
        collection = pipeline.client.collections.get(COLLECTION_NAME)
        count = collection.aggregate.over_all(
            group_by=GroupByAggregate(prop="file_name", limit=1000)
        )
        docs = [group.grouped_by.value for group in count.groups]
        if file_name not in docs:
            return {"error": "File not found."}

        filter_criteria = wvc.query.Filter.by_property("file_name").equal(file_name)
        delete_result = collection.data.delete_many(where=filter_criteria)
        if delete_result.successful:
            return {"message": "File deleted successfully."}
        return {"error": "Failed to delete the file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/delete")
async def delete_weaviate_collection() -> Dict:
    """
    Delete the entire collection from the vector database.

    Returns:
        dict: A message confirming the deletion of the collection.

    Raises:
        HTTPException: If the deletion fails.
    """
    try:
        pipeline.client.collections.delete(COLLECTION_NAME)
        return {"message": "Collection deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/name")
async def get_collection_name() -> Dict:
    """
    Get the name of the current collection in the vector database.

    Returns:
        dict: A dictionary containing the collection name.

    Raises:
        HTTPException: If the query fails.
    """
    try:
        return {"collection_name": COLLECTION_NAME}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/collections/name_all")
async def get_collection_names() -> Dict:
    """
    Get a list of all collections in the vector database.

    Returns:
        dict: A dictionary with the names of all collections.

    Raises:
        HTTPException: If the query fails.
    """
    try:
        collections = pipeline.client.collections.list_all(simple=False).keys()
        return {"collections": list(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/read_files")
async def read_files_from_collection() -> Dict:
    """
    """
    try:
        collection = pipeline.client.collections.get(COLLECTION_NAME)

        # Perform an aggregate query to get unique files and their chunk counts
        response = collection.aggregate.over_all(
            group_by=GroupByAggregate(prop="file_name", limit=1000),
            total_count=True
        )
        result = [
            {
                "file_name": group.grouped_by.value,
                "num_chunks": group.total_count
            }
            for group in response.groups
        ]

        # get rest of properties for each file
        for file in result:
            filter_criteria = wvc.query.Filter.by_property("file_name").equal(file["file_name"])

            file_properties = collection.query.fetch_objects(
                filters=filter_criteria, 
                limit=1,
                return_properties=["author", "date", "region", "size", "language", "upload_time"]
                ).objects[0].properties

            file["date"] = file_properties["date"]
            file["author"] = file_properties["author"]
            file["region"] = file_properties["region"]
            file["size"] = file_properties["size"]
            file["language"] = file_properties["language"]
            file["upload_time"] = file_properties["upload_time"]
            file["url"] = FILE_SYSTEM_SERVER + "/" +  file["file_name"]
        
        return {"files": result}


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/collections/read_all")
async def read_all_collection() -> Dict:
    """
    Read all documents from the collection.

    Returns:
        dict: A dictionary containing all documents in the collection.

    Raises:
        HTTPException: If the query fails.
    """
    try:
        all_objects = []
        pdf_docs = pipeline.client.collections.get(COLLECTION_NAME)
        for item in pdf_docs.iterator(cache_size=50):
            properties = item.properties
            all_objects.append(properties)
            
        return {"all_objects": all_objects}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/collections/insert")
async def insert(
        file_name: str,
        chunks: List[str],
        author: str,
        date: Optional[str] = "",
        region: Optional[str] = "",
        size: Optional[float] = 0.0,
        language: Optional[str] = "latin-based",
        upload_time: Optional[str] = ""
        ) -> Dict:
    

    chunks = [
        Chunk(
            file_name=file_name,
            content=content,
            author=author,
            date=date,
            region=region,
            size=size,
            language=language,
            upload_time=upload_time
        )
        for content in chunks
    ]

    try:
        pipeline.run(chunks=chunks)
        return {
            "num_chunks": len(chunks)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retrieve")
async def run_semantic_query(query: str) -> Dict:
    """
    Run a semantic query to retrieve evidence from the collection.

    Parameters:
        query (str): The query string to search for.

    Returns:
        dict: A dictionary containing ranked evidence, confidence scores, and the query.

    Raises:
        HTTPException: If the retrieval process fails.
    """
    try:
        pdf_docs = pipeline.client.collections.get(COLLECTION_NAME)
        response = pdf_docs.query.near_text(
            query=f"{query}",
            limit=5,
            return_metadata=MetadataQuery(
                certainty=True,
                )
        )
        confidence_scores: List[float] = []
        evidences: List[Dict] = []

        for o in response.objects:
            confidence_score = o.metadata.certainty
            evidence = o.properties

            confidence_scores.append(confidence_score)
            evidences.append(evidence)
        
        rank_scores = rank(RERAKER, query, evidences)
        
        # Sort the evidences and confidence scores based on the rank scores
        ranked_evidences = [
            {
                "evidence": i,
                "confidence_score": j,
                "rank_score": k
            }

            for i, j, k in sorted(
                zip(evidences, confidence_scores, rank_scores),
                key=lambda x: x[2],
                reverse=True
            )
        ]

        return {
            "pdf_docs": {
                "search": {
                    "query": query,
                },
                "artifacts": ARTIFACTS,
                "evidences": ranked_evidences
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retrieve/filter")
async def run_filter_query(
    query: str, 
    author: Optional[str] = "", 
    date: Optional[str] = "", 
    region: Optional[str] = "",
    file_name: Optional[str] = "",
    top_k: Optional[Union[float, int]] = 5
    ):
    """
    Run a filtered query on the collection.

    Parameters:
        query (str): The query string to search for.
        author (str, optional): Filter by author.
        date (str, optional): Filter by date.
        region (str, optional): Filter by region.
        file_name (str, optional): Filter by file name.
        top_k (int, optional): Number of top results to return (default: 5).

    Returns:
        dict: A dictionary containing ranked evidence filtered by the specified attributes.

    Raises:
        HTTPException: If the query or filtering fails.
    """
    try:
        # Initialize filters list
        filters = []

        # Add each filter conditionally based on provided parameters
        if author:
            filters.append(wvc.query.Filter.by_property("author").equal(author))
        if date:
            filters.append(wvc.query.Filter.by_property("date").equal(date))
        if region:
            filters.append(wvc.query.Filter.by_property("region").equal(region))
        if file_name:
            filters.append(wvc.query.Filter.by_property("file_name").equal(file_name))

        # Combine filters if there are any; use "and" to require all conditions to match
        filter_expr = None
        if filters:
            filter_expr = wvc.query.Filter.all_of(filters)

        # Query the Vector DB with the constructed filters
        pdf_docs = pipeline.client.collections.get(COLLECTION_NAME)
        if int(top_k) != top_k:
            response = pdf_docs.query.near_text(
                query=query,
                certainty=top_k,
                filters=filter_expr,
                target_vector="content_vector",
                return_metadata=MetadataQuery(
                    certainty=True,
                    )
            )
        else:
            response = pdf_docs.query.near_text(
                query=query,
                limit=int(top_k),
                filters=filter_expr,
                target_vector="content_vector",
                return_metadata=MetadataQuery(
                    certainty=True,
                    )
            )

        confidence_scores: List[float] = []
        evidences: List[Dict] = []

        for o in response.objects:
            confidence_score = o.metadata.certainty
            evidence = o.properties

            confidence_scores.append(confidence_score)
            evidences.append(evidence)
        
        rank_scores = rank(RERAKER, query, evidences)

        ranked_evidences = [
            {
                "evidence": i,
                "confidence_score": j,
                "rank_score": k
            }

            for i, j, k in sorted(
                zip(evidences, confidence_scores, rank_scores),
                key=lambda x: x[2],
                reverse=True
            )
        ]

        return {
            "pdf_docs": {
                "search": {
                    "query": query,
                    "author": author,
                    "date": date,
                    "region": region,
                    "file_name": file_name,
                    "top_k": top_k
                },
                "artifacts": ARTIFACTS,
                "evidences": ranked_evidences
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/generate/stance")
async def generate_stance(query: str, evidence: str, author: Optional[str] = None) -> Dict:
    """
    Generate a stance based on a query and evidence.

    Parameters:
        query (str): The query string.
        evidence (str): The evidence string.
        metadata (dict, optional): Additional metadata for the generation process.

    Returns:
        dict: A dictionary containing the stance score and reason.

    Raises:
        HTTPException: If the generation process fails.
    """
    try:
        generated_stance = generate(
            GENERATOR, 
            evidence, 
            query, 
            author
            )
        
        return {
            "stance": generated_stance["score"],
            "stance_text": generated_stance["stance_text"],
            "stance_score": 0.0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/generate/rag")
async def rag(
        query: str,
        author: Optional[str] = "",
        date: Optional[str] = "",
        region: Optional[str] = "",
        file_name: Optional[str] = "",
        top_k: Optional[int] = 5
    ) -> Dict:
    """
    Run a full retrieval-augmented generation (RAG) process.

    Parameters:
        query (str): The query string to search for.
        author (str, optional): Filter by author.
        date (str, optional): Filter by date.
        region (str, optional): Filter by region.
        file_name (str, optional): Filter by file name.
        top_k (int, optional): Number of top results to return (default: 5).

    Returns:
        dict: A dictionary containing ranked evidence and generated stance.

    Raises:
        HTTPException: If the RAG process fails.
    """
    try:
        # Initialize filters list
        filters = []

        # Add each filter conditionally based on provided parameters
        if author:
            filters.append(wvc.query.Filter.by_property("author").equal(author))
        if date:
            filters.append(wvc.query.Filter.by_property("date").equal(date))
        if region:
            filters.append(wvc.query.Filter.by_property("region").equal(region))
        if file_name:
            filters.append(wvc.query.Filter.by_property("file_name").equal(file_name))

        # Combine filters if there are any; use "and" to require all conditions to match
        filter_expr = None
        if filters:
            filter_expr = wvc.query.Filter.all_of(filters)

        # Query the Vector DB with the constructed filters
        pdf_docs = pipeline.client.collections.get(COLLECTION_NAME)
        response = pdf_docs.query.near_text(
            query=query,
            limit=top_k,
            filters=filter_expr,
            return_metadata=MetadataQuery(
                certainty=True,
                )
        )

        confidence_scores: List[float] = []
        evidences: List[Dict] = []

        for o in response.objects:
            confidence_score = o.metadata.certainty
            evidence = o.properties

            confidence_scores.append(confidence_score)
            evidences.append(evidence)
        
        rank_scores = rank(RERAKER, query, evidences)
        ranked_evidences = [
            {
                "evidence": i,
                "confidence_score": j,
                "rank_score": k
            }

            for i, j, k in sorted(
                zip(evidences, confidence_scores, rank_scores),
                key=lambda x: x[2],
                reverse=True
            )
        ]
       
        # Call LLM
        stances = []
        for evd in ranked_evidences:
            stance = generate(
                GENERATOR, 
                evd["evidence"]["content"], 
                query, 
                evd["evidence"]["author"]
                )
            stances.append(stance)

        for i, evd in enumerate(ranked_evidences):
            evd["stance"] = stances[i]["score"]
            evd["stance_text"] = stances[i]["stance_text"]
            evd["stance_score"] = 0.0
    
     
        return {
            "pdf_docs": {
                "search": {
                    "query": query,
                    "author": author,
                    "date": date,
                    "region": region,
                    "file_name": file_name,
                    "top_k": top_k
                },
                "evidences": ranked_evidences
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



