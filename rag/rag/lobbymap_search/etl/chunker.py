import re
from typing import List, Literal, Optional
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.cluster import AgglomerativeClustering



class LayoutChunking:
    def __init__(
            self,
            token_limit: Optional[int] = None,
            tokenizer_model: Optional[str] = "bert-base-uncased"
            ):
        
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_model)
        self.token_limit = token_limit

    def chunk(self, markdown_text: str) -> List[str]:
        """
        """
        lines = markdown_text.strip().splitlines()
        chunks = []
        current_chunk = []
        title_pattern = re.compile(r'^#+ ')

        for line in lines:
            line = line.strip()
            if not line:  # Ignore empty lines
                continue
            if title_pattern.match(line):
                if current_chunk and not any(not title_pattern.match(l) for l in current_chunk):
                    current_chunk.append(line)
                else:
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk).strip())
                    current_chunk = [line]
            else:
                current_chunk.append(line)

        # Finalize the last chunk
        if current_chunk:
            if chunks and not any(not title_pattern.match(l) for l in current_chunk):
                chunks[-1] += '\n' + '\n'.join(current_chunk).strip()
            else:
                chunks.append('\n'.join(current_chunk).strip())
        
        # Apply token limit to chunks
        if self.token_limit is not None:
            limited_chunks = []
            for chunk in chunks:
                limited_chunks.extend(self._split_to_token_limit(chunk))
            return limited_chunks
        
        return chunks

    def _split_to_token_limit(self, text: str) -> List[str]:
        """
        Splits a text into smaller chunks, ensuring each chunk is within the token limit.

        :param text: The text to split.
        :param token_limit: The maximum number of tokens allowed per chunk.
        :return: A list of token-limited chunks.
        """
        tokens = self.tokenizer(text)["input_ids"]
        if len(tokens) <= self.token_limit:
            return [text]
        
        token_chunks = []
        current_tokens = []
        current_text = []

        for word in text.split():
            word_tokens = self.tokenizer(word, add_special_tokens=False)["input_ids"]
            if len(current_tokens) + len(word_tokens) > self.token_limit:
                token_chunks.append(self.tokenizer.decode(
                    current_tokens, 
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                    ).strip())
                current_tokens = word_tokens
                current_text = [word]
            else:
                current_tokens.extend(word_tokens)
                current_text.append(word)

        if current_tokens:
            token_chunks.append(self.tokenizer.decode(
                current_tokens, 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
                ).strip())
        return token_chunks


class SemanticChunking:
    def __init__(
            self, 
            similarity_threshold: Optional[float] = 0.8,
            model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"
            ):
        """
        """

        self.similarity_threshold = similarity_threshold
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate a semantic embedding for a given piece of text.
        :param text: Input text to generate embedding for.
        :return: A numpy array representing the semantic embedding.
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Pooling strategy: We take the mean of the token embeddings
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        return embedding

    def chunk(self, text: str) -> np.ndarray:
        """
        Splits the text into semantically coherent chunks by using sentence embeddings
        and grouping sections based on their semantic similarity, regardless of order.

        :param text: The text as a single string.
        :param similarity_threshold: The threshold for merging chunks based on semantic similarity (default: 0.8).
        :return: A list of semantically coherent chunks.
        """
        lines = text.strip().splitlines()
        line_embeddings = []
        valid_lines = []

        # Embed all lines and store their embeddings
        for line in lines:
            line = line.strip()
            if not line:  # Ignore empty lines
                continue
            valid_lines.append(line)
            embedding = self.embed_text(line)
            line_embeddings.append(embedding)

        # Convert list to numpy array
        line_embeddings = np.array(line_embeddings)

        # Compute the pairwise cosine similarity matrix
        similarity_matrix = self.compute_similarity_matrix(line_embeddings)

        # Clustering the lines based on similarity
        clustering = AgglomerativeClustering(n_clusters=None, metric='precomputed', linkage='complete', distance_threshold=(1 - self.similarity_threshold))
        clusters = clustering.fit_predict(1 - similarity_matrix)

        # Group lines based on their clusters
        clustered_lines = {}
        for idx, cluster_id in enumerate(clusters):
            if cluster_id not in clustered_lines:
                clustered_lines[cluster_id] = []
            clustered_lines[cluster_id].append(valid_lines[idx])

        # Merge clustered lines into chunks
        chunks = ['\n'.join(clustered_lines[cluster_id]) for cluster_id in sorted(clustered_lines)]

        return chunks
    
    @staticmethod
    def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes cosine similarity between two vectors.
        :param emb1: First embedding (1-D numpy array).
        :param emb2: Second embedding (1-D numpy array).
        :return: Cosine similarity value.
        """
        dot_product = np.dot(emb1, emb2)
        norm_emb1 = np.linalg.norm(emb1)
        norm_emb2 = np.linalg.norm(emb2)
        return dot_product / (norm_emb1 * norm_emb2)
    

    
    def compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Computes the cosine similarity matrix for the set of embeddings.
        :param embeddings: 2D array where each row is an embedding.
        :return: A 2D numpy array representing the cosine similarity matrix.
        """
        num_embeddings = embeddings.shape[0]
        similarity_matrix = np.zeros((num_embeddings, num_embeddings))
        for i in range(num_embeddings):
            for j in range(num_embeddings):
                if i == j:
                    similarity_matrix[i, j] = 1.0  # Self-similarity is always 1
                else:
                    similarity_matrix[i, j] = self.compute_cosine_similarity(embeddings[i], embeddings[j])
        return similarity_matrix






class TextChunker:
    def __init__(
            self, 
            method: Literal["layout", "semantic"] = "layout",
            chunking_options: dict = {}
            ):
        """
        Initialize the chunker with the specified method.
        :param method: The chunking method to use ("layout" or "semantic").
        """
        if method.lower() == "layout":
            self.chunker = LayoutChunking(**chunking_options)
        elif method.lower() == "semantic":
            self.chunker = SemanticChunking(**chunking_options)
        else:
            raise ValueError(f"Invalid chunking method: {method}")


    def chunk(self, text: str) -> List[str]:
        """
        Chunk the input text using the specified method.
        :param text: The input text as a single string.
        :param kwargs: Additional keyword arguments for the chunking method.
        :return: A list of chunks, each as a string.
        """
        return self.chunker.chunk(text)





