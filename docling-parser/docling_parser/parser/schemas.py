from typing import Optional, Literal
from typing_extensions import Self
from pydantic import BaseModel, model_validator
import os



class DocumentInput(BaseModel):
    file_path: str
    size: float = 0.0
    language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based"

    @model_validator(mode='after')
    def verify_size(self) -> Self:
        """
        """
        if self.size == 0.0:
            # Get file size in MB
            self.size = os.path.getsize(self.file_path) / (1024 * 1024)
            # round to 2 decimal places
            self.size = round(self.size, 2)
        
        else:
            self.size = round(self.size, 2)
        return self
