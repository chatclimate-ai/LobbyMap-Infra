from typing import List
from chonkie import SemanticChunker, SDPMChunker
from chonkie import SentenceTransformerEmbeddings


class SemanticChunking:
    def __init__(
            self, 
            model="nomic-ai/nomic-embed-text-v1.5", 
            chunk_size=1536, 
            similarity_threshold=0.8, 
            double_pass_merge=True,
            device="cpu"
            ) -> None:
        self.model = SentenceTransformerEmbeddings(
            model, 
            trust_remote_code=True, 
            device= device
            )
        self.chunk_size = chunk_size
        self.threshold = similarity_threshold
        if double_pass_merge:
            self.chunker = SDPMChunker(
                embedding_model=self.model,
                threshold=self.threshold,
                chunk_size=self.chunk_size,
            )
        else:
            self.chunker = SemanticChunker(
                embedding_model=self.model,
                threshold=self.threshold,
                chunk_size=self.chunk_size,
            )
    def chunk(self, text: str) -> List[str]:
        chunks = self.chunker.chunk(text)
        chunk_texts = [chunk.text for chunk in chunks]
        return chunk_texts
