from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, List, Literal
from docling_parser.parser.schemas import DocumentInput
from docling_parser.parser.pipeline import ParserPipeline
import yaml

description = """
"""

config_path = "/app/config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)



FILE_SYSTEM = config["Backend"]["file_system"]

PARSER = config["parser_options"]["parser"]
SAVE_PARSED_CONTENT = config["parser_options"]["save_parsed_content"]
MD_OUTPUT_DIR = FILE_SYSTEM + "/" + config["parser_options"]["output_dir"]
PARSER_OPTIONS = config[config["parser_options"]["parser_options"]]

CHUNKING_METHOD = config["Chunker"]["chunking_method"]
CHUNKING_OPTIONS = config[config["Chunker"]["chunking_options"]]


parser = ParserPipeline(
    parser=PARSER,
    parser_options=PARSER_OPTIONS,
    save_locally=SAVE_PARSED_CONTENT,
    save_dir=MD_OUTPUT_DIR,
    chunking_method=CHUNKING_METHOD,
    chunking_options=CHUNKING_OPTIONS
)




app = FastAPI(
    title="PDF Parsing API",
    description=description,
    summary= ""
    )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to the origin of your frontend if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/parse")
async def parse_pdf(
    file_path: str,
    size: float = 0.0,
    language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based"
) -> Dict:
    """
    """
    try:
        params = DocumentInput(
            file_path=file_path,
            size=size,
            language=language
        )
        chunks: List[str] = parser.run(params)
        return {"chunks": chunks}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))









