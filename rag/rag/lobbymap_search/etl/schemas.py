from typing import Optional, Literal
from typing_extensions import Self
from pydantic import BaseModel, model_validator


  
class Chunk(BaseModel):
    file_name: str
    content: str
    author: str
    date: Optional[str] = ""
    region: Optional[str] = ""
    size: Optional[float] = 0.0
    language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based"
    upload_time: Optional[str] = ""

    @model_validator(mode='after')
    def verify_size(self) -> Self:
        """
        """
        if self.size > 0.0:
            self.size = round(self.size, 2)
        return self
    
    @model_validator(mode='after')
    def lower_case(self) -> Self:
        """
        """
        self.author = self.author.lower()
        self.date = self.date.lower()
        self.region = self.region.lower()
        self.language = self.language.lower()
        return self
