from .schemas import PdfDocument, MarkdownDocument, DocumentInput
from .parser import PDFParser
from .chunker import TextChunker
from typing import List, Dict, Literal
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from dotenv import load_dotenv
import os
import re
import logging
import warnings
import gc

warnings.filterwarnings("ignore", category=DeprecationWarning)


load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PdfDocumentPipeline:
    """
    An ETL pipeline to extract, process and load the parsed pdf documents into the vector DB.
    """
    parsed_pdfs: List[PdfDocument] = None
    parsed_pdf_dicts: List[Dict] = None
    pdf_serializer: PDFParser
    chunker: TextChunker

    def __init__(
            self,
            collection_name: str = "PdfDocument",
            parser: Literal["docling", "pymupdf"] = "docling",
            parser_options: Dict = {},
            save_locally: bool = False, 
            save_dir: str = "output",
            chunking_method: Literal["layout", "semantic"] = "layout",
            chunking_options: Dict = {},
            vectorizer: str = "bge-m3",
            close_client: bool = False
            ):
        """
        Initialize the pipeline by connecting to the Vector DB and creating the PubmedArticle collection.
        """
        self.pdf_serializer = PDFParser(
            parser, 
            parser_options=parser_options,
            save_locally=save_locally,
            save_dir=save_dir
            )
        self.chunker = TextChunker(chunking_method, chunking_options)
        self.collection_name = collection_name
        self.vectorizer = vectorizer
        self.pdfdocument_client = None
        self.close_client = close_client
        

    def connect_to_weaviate(self):
        """
        Connect to Weaviate and initialize the PdfDocument collection if it doesn't exist.
        """
        if self.pdfdocument_client is None:
            logger.info("Connecting to Weaviate...")
            try:
                self.pdfdocument_client = weaviate.connect_to_custom(
                    http_host="weaviate",
                    http_port=8080,
                    http_secure=False,
                    grpc_host="weaviate",
                    grpc_port=50051,
                    grpc_secure=False,
                )

                if not self.pdfdocument_client.collections.exists(self.collection_name):
                    logger.info("Creating PdfDocument collection...")
                    self.pdfdocument_client.collections.create(
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
                            Property(name="content", data_type=DataType.TEXT),
                        ]
                    )
                
                else:
                    logger.info("PdfDocument collection already exists.")

            except Exception as e:
                if self.pdfdocument_client is not None:
                    self.pdfdocument_client.close()
                raise e

    def close(self):
        if self.pdfdocument_client is not None:
            self.pdfdocument_client.close()
            self.pdfdocument_client = None


    def _extract(self, pdf_files: List[DocumentInput]):
        """
        Extract the parsed pdf document content and metadata.
        """
        self.parsed_pdfs = []
        

        for file in pdf_files:
            if not os.path.isfile(file.file_path):
                raise ValueError(f"File not found: {file.file_path}")
            
            if file.file_path.lower().endswith(".pdf"):
                doc = self.pdf_serializer.parse_file(file)
            
            elif file.file_path.lower().endswith(".md"):
                with open(file.file_path, "r") as f:
                    content = f.read()
                
                doc = MarkdownDocument(
                    file_name = os.path.basename(file.file_path),
                    content=content,
                    **file.metadata.model_dump()
                )
            
            else:
                raise ValueError(f"Unsupported file format: {file.file_path}")
            

            # Post-processing
            # remove glyph placeholders
            regex_pattern = r"GLYPH<[^>]+>"
            doc.content = re.sub(regex_pattern, "", doc.content).strip()

            # remove image placeholders
            regex_pattern = r"<!-- image -->"
            doc.content = re.sub(regex_pattern, "", doc.content).strip()

            regex_pattern = r"\\{1,2}_"
            doc.content = re.sub(regex_pattern, ".", doc.content).strip()

            if not doc.content:
                doc.content = "File is empty after Parsing"

            # Chunk the parsed content
            for chunk in self.chunker.chunk(doc.content):
                if doc.file_name.endswith(".pdf"):
                    self.parsed_pdfs += [
                        PdfDocument(
                            file_name=doc.file_name,
                            author=doc.author,
                            date=doc.date,
                            region=doc.region,
                            size=doc.size,
                            language=doc.language,
                            content=chunk
                        )
                    ]
                else:
                    self.parsed_pdfs += [
                        MarkdownDocument(
                            file_name=doc.file_name,
                            author=doc.author,
                            date=doc.date,
                            region=doc.region,
                            size=doc.size,
                            language=doc.language,
                            content=chunk
                        )
                    ]




    def _transform(self):
        """
        Transform the parsed pdf documents into dicts:
        """
        if self.parsed_pdfs is None:
            raise ValueError("No chunks created. Please run the extract method first.")
        
        self.parsed_pdf_dicts = []
        for pdf_doc in self.parsed_pdfs:
            self.parsed_pdf_dicts += [
                pdf_doc.model_dump()
            ]


    def _load_into_vdb(self):
        """
        Loading the PdfDocument objects into the Vector DB
        """
        if self.parsed_pdf_dicts is None:
            raise ValueError("No chunk dicts created. Please run the transform method first.")

        self.connect_to_weaviate()

        # loading into the Vector DB
        try:
            collection = self.pdfdocument_client.collections.get(self.collection_name)
            with collection.batch.fixed_size(batch_size=5) as batch:
                for pdf_doc in self.parsed_pdf_dicts:
                    batch.add_object(properties=pdf_doc)
            
            failed_objs = collection.batch.failed_objects
            if failed_objs:
                for failed_obj in failed_objs:
                    logger.error(f"Failed to load object into the Vector DB: {failed_obj}\n")
                raise Exception(f"Failed to load objects into the Vector DB. {failed_obj}")
            else:
                logger.info("All objects were successfully added.")

            gc.collect()
        except Exception as e:
            logger.error(f"Failed to load chunked pdf doc into the Vector DB: {e}")
            raise e
            
        
    def run(self, pdf_files: List[DocumentInput]):
        """
        Run the ETL pipeline to extract, transform and load the parsed pdf documents into the Vector DB.
        """
        try:
            self._extract(pdf_files=pdf_files)
            self._transform()
            self._load_into_vdb()

            return self.parsed_pdf_dicts
        
        except Exception as e:
            logger.error(f"An error occurred during the pipeline execution: {e}")
            raise e
        finally:
            if self.close_client:
                self.close()
            logger.info("Pipeline execution completed successfully.")
