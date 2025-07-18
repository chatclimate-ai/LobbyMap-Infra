from .schemas import Chunk
from typing import List, Dict
import weaviate
from weaviate.classes.config import Configure, Property, DataType
import logging
import warnings
import gc

warnings.filterwarnings("ignore", category=DeprecationWarning)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PdfDocumentPipeline:
    """
    An ETL pipeline to extract, process and load the parsed pdf documents into the vector DB.
    """
    chunks: List[Chunk] = None
    chunk_dicts: List[Dict] = None

    def __init__(
            self,
            collection_name: str = "PdfDocument",
            vectorizer: str = "bge-m3",
            close_client: bool = False
            ):
        """
        Initialize the pipeline by connecting to the Vector DB and creating the PubmedArticle collection.
        """
        self.collection_name = collection_name
        self.vectorizer = vectorizer
        self.client = None
        self.close_client = close_client
        

    def connect_to_weaviate(self):
        """
        Connect to Weaviate and initialize the PdfDocument collection if it doesn't exist.
        """
        if self.client is None:
            logger.info("Connecting to Weaviate...")
            try:
                self.client = weaviate.connect_to_custom(
                    http_host="weaviate",
                    http_port=8080,
                    http_secure=False,
                    grpc_host="weaviate",
                    grpc_port=50051,
                    grpc_secure=False,
                )

                if not self.client.collections.exists(self.collection_name):
                    logger.info(f"Creating {self.collection_name} collection...")
                    self.client.collections.create(
                        name=self.collection_name,
                        vectorizer_config= [
                            Configure.NamedVectors.text2vec_ollama(
                                name="content_vector",
                                source_properties=["content"],
                                model= self.vectorizer,
                                api_endpoint="http://host.docker.internal:11434"
                            )
                        ],
                   
                        properties=[
                            Property(name="file_name", data_type=DataType.TEXT),
                            Property(name="author", data_type=DataType.TEXT),
                            Property(name="date", data_type=DataType.TEXT),
                            Property(name="region", data_type=DataType.TEXT),
                            Property(name="size", data_type=DataType.NUMBER),
                            Property(name= "language", data_type=DataType.TEXT),
                            # Property(name="upload_time", data_type=DataType.TEXT),
                            Property(name="content", data_type=DataType.TEXT),
                        ]
                    )
                
                else:
                    logger.info(f"{self.collection_name} collection already exists.")

            except Exception as e:
                if self.client is not None:
                    self.client.close()
                raise e

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None



    @staticmethod
    def _transform(chunks: List[Chunk]) -> List[Dict]:
        """
        Transform the list of Chunk objects into a list of dictionaries.
        """
        if not chunks:
            raise ValueError("Empty list of chunks. Please provide a list of chunks to transform.")
        
        chunk_dicts = []
        for chunk in chunks:
            chunk_dicts += [
                chunk.model_dump()
            ]
        
        return chunk_dicts


    def _load_into_vdb(self, chunk_dicts: List[Dict]):
        """
        Stream chunks into Weaviate in small memory-safe batches.
        """
        if not chunk_dicts:
            raise ValueError("No chunk dicts created. Please run the transform method first.")

        self.connect_to_weaviate()
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Process in batches to avoid RAM overload
            BATCH_SIZE = 5
            for i in range(0, len(chunk_dicts), BATCH_SIZE):
                mini_batch = chunk_dicts[i:i+BATCH_SIZE]
                with collection.batch.fixed_size(batch_size=BATCH_SIZE) as batch:
                    for chunk in mini_batch:
                        batch.add_object(properties=chunk)
                
                failed_objs = collection.batch.failed_objects
                if failed_objs:
                    for failed_obj in failed_objs:
                        logger.error(f"Failed to load object: {failed_obj}")
                    raise Exception(f"Failed to load some objects into Vector DB.")
                
                del mini_batch
                gc.collect()
            
            logger.info("All objects successfully added to Weaviate.")

        except Exception as e:
            logger.error(f"Failed to load chunks: {e}")
            raise

            
        
    def run(self, chunks: List[Chunk]):
        """
        Run the ETL pipeline to extract, transform and load the parsed pdf documents into the Vector DB.
        """
        try:
            chunk_dicts = self._transform(chunks=chunks)
            self._load_into_vdb(chunk_dicts=chunk_dicts)
        
        except Exception as e:
            logger.error(f"An error occurred during the pipeline execution: {e}")
            raise e
        finally:
            if self.close_client:
                self.close()
            logger.info("Pipeline execution completed successfully.")
