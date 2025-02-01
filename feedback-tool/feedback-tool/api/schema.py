from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class EvidenceSearchModel(BaseModel):
    searched_query: str = Field(
        ...,
        description="The query that was used to search for evidence",
    )
    searched_author: Optional[str] = Field(
        default=None,
        description="The author that was used to search for evidence",
    )
    searched_date: Optional[str] = Field(
        default=None,
        description="The date that was used to search for evidence",
    )
    searched_region: Optional[str] = Field(
        default=None,
        description="The region that was used to search for evidence",
    )
    searched_file_name: Optional[str] = Field(
        default=None,
        description="The file name that was used to search for evidence",
    )
    top_k: int = Field(
        ...,
        description="The number of top evidences to be retrieved",
    )


class ParserModel(BaseModel):
    model_name: str = Field(
        ...,
        description="The name of the parser model",
    )
    options: Optional[dict] = Field(
        default=None,
        description="The options of the parser model",
    )

class ChunkerModel(BaseModel):
    chunking_method: str = Field(
        ...,
        description="The method used to chunk the evidence",
    )
    options: Optional[dict] = Field(    
        default=None,
        description="The options of the chunker model",
    )

class RAGComponents(BaseModel):
    collection_name: str = Field(
        ...,
        description="The name of the collection in weaviate",
    )
    vectorizer_model_name: str = Field(
        ...,
        description="The name of the vectorizer model",
    )
    reranker_model_name: str = Field(
        ...,
        description="The name of the reranker model",
    )
    generator_model_name: str = Field(
        ...,
        description="The name of the generator model",
    )

class Artifacts(BaseModel):
    parser: ParserModel
    chunker: ChunkerModel
    rag_components: RAGComponents
class EvidenceModel(BaseModel):
    """
    The model class that represents the chunk evidence to be sent back
    """
    search_elements: EvidenceSearchModel = Field(
        ...,
        description="The search elements that were used to retrieve the evidence",
    )
    pdf_doc_name: str = Field(
        ...,
        description="The name of the pdf document that the evidence was retrieved from",
    )
    content: str = Field(
        ...,
        description="The content of the evidence",
    )
    author: Optional[str] = Field(
        default=None,
        description="The name of the company that the evidence was retrieved from",
    )
    date: Optional[str] = Field(
        default=None,
        description="The applied to the retrieved evidence",
    )
    region: Optional[str] = Field(
        default=None,
        description="The region where the evidence comes from",
    )
    rank: int = Field(
        ...,
        description="The rank of the evidence among the retrieved evidences, coming from RAG",
    )
    status: Literal['approved', 'rejected'] = 'approved'
    confidence_score: float = Field(
        ...,
        description="The confidence score of the evidence coming from the embedding model",
    )
    rank_score: float = Field(
        ...,
        description="The rank score of the evidence coming from the ranker model",
    )
    generated_stance: Optional[int] = Field(
        default=None,
        description="The stance generated for the evidence by the LLM model",
    )
    generated_stance_reason: Optional[str] = Field(
        default=None,
        description="The reason for the stance generated for the evidence by the LLM model",
    )
    generated_stance_score: Optional[float] = Field(
        default=None,
        description="The stance score generated for the evidence by the LLM model",
    )
    updated_rank: int = Field(
        ...,
        description="The updated rank after feedback",
    )
    updated_status: Optional[Literal['approved', 'rejected']] = Field(
        default="approved",
        description="The updated status after feedback",
    )
    updated_generated_stance: Optional[int] = Field(
        default=None,
        description="The updated stance after feedback",
    )
    timestamp: str = Field(
        ...,
        description="The timestamp of the feedback",
    )
    artifacts: Artifacts = Field(
        ...,
        description="The artifacts used in the RAG engine",
    )


class FeedbackResponseModel(EvidenceModel):
    id: str


class FeedbackCollection(BaseModel):
    feedbacks: List[FeedbackResponseModel]
