from typing import Optional
from typing_extensions import Self
from pydantic import BaseModel, Field, model_validator, ConfigDict
import os


class InputMetadata(BaseModel):
    """
    InputMetadata schema for handling metadata using Pydantic V2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    author: str
    date: Optional[str] = ""
    region: Optional[str] = ""
    size: Optional[float] = 0.0


class DocumentInput(BaseModel):
    """
    DocumentInput schema for handling input documents using Pydantic V2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_path: str
    metadata: InputMetadata

    @model_validator(mode='after')
    def verify_size(self) -> Self:
        """
        """
        if self.metadata.size == 0.0:
            # Get file size in MB
            self.metadata.size = os.path.getsize(self.file_path) / (1024 * 1024)
            # round to 2 decimal places
            self.metadata.size = round(self.metadata.size, 2)
        return self



class Chunk(BaseModel):
    """
    PdfChunk schema for handling text chunks extracted from PDF files using Pydantic V2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source_file_name: str
    source_file_author: str
    content: str
    page_num: int
    chunk_type: Optional[str] = "text"
    source_file_date: Optional[str] = ""
    source_file_region: Optional[str] = ""
  



class PdfDocument(BaseModel):
    """
    PdfDocument schema for handling PDF files using Pydantic V2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_name: str
    author: str
    date: Optional[str] = ""
    region: Optional[str] = ""
    size: Optional[float] = 0.0
    content: str = Field(default="")

    @model_validator(mode='after')
    def verify_file_path(self) -> Self:
        """
        """ 
        if not self.file_name.lower().endswith('.pdf'):
            raise ValueError("file_name must be a PDF file.")
    

        return self     


class MarkdownDocument(BaseModel):
    """
    MarkdownDocument schema for handling markdown files using Pydantic V2.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_name: str
    author: str
    date: Optional[str] = ""
    region: Optional[str] = ""
    size: Optional[float] = 0.0
    content: str = Field(default="")

    @model_validator(mode='after')
    def verify_file_path(self) -> Self:
        """
        """
        if not self.file_name.lower().endswith('.md'):
            raise ValueError("file_name must be a markdown file.")
        
        # Remove front matter
        if self.content.startswith("---"):
            self.content = self.content.split("---", 2)[2]
    
        return self     
