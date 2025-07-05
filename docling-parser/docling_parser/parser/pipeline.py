from typing import Literal, List
from docling_parser.parser.docling_parse import DoclingPDFParser, DoclingParserLarge
from docling_parser.parser.schemas import DocumentInput
from docling_parser.parser.chunker import SemanticChunking
import logging
import os
import time
import re


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ParserPipeline:
    """
    PDFParser class for parsing PDF files.
    """

    def __init__(
            self, 
            parser: Literal["docling"] = "docling",
            parser_options: dict = {},
            save_locally: bool = False, 
            save_dir: str = "output",
            chunking_method: str = "Semantic",
            chunking_options: dict = {}
            ):
        """
        Initializes the PDFParser object.
        """
        if parser == "docling":
            self.parser = DoclingPDFParser()
            self.parser_large= DoclingParserLarge()
        else:
            raise ValueError(f"Invalid parser specified: {parser}")

        self.save_locally = save_locally
        self.save_dir = save_dir
        self.parser_options = parser_options

        if chunking_method == "Semantic":
            self.chunker = SemanticChunking(**chunking_options)
        else:
            raise ValueError(f"Invalid chunking method specified: {chunking_method}")

    @staticmethod
    def post_process(content: str) -> str:
        # remove glyph placeholders
        regex_pattern = r"GLYPH<[^>]+>"
        content = re.sub(regex_pattern, "", content).strip()

        # remove image placeholders
        regex_pattern = r"<!-- image -->"
        content = re.sub(regex_pattern, "", content).strip()

        regex_pattern = r"\\{1,2}_"
        content = re.sub(regex_pattern, ".", content).strip()

        if not content:
            content = "File is empty after Parsing"
        
        return content

    def chunk_file(
            self,
            content: str
    ) -> List[str]:
        """
        """
        return self.chunker.chunk(content)

    def parse_file(
            self, 
            input_data: DocumentInput,
            ) -> str:
        """
        """
        # Parse the PDF file and extract text content
        start_time = time.time()
        content = self.parse(input_data)
        end_time = time.time()
        logger.info(f"Time taken to parse the file: {end_time - start_time:.2f} seconds")


        # Save the parsed content to a markdown file
        if self.save_locally:
            file_name = os.path.basename(input_data.file_path)
            os.makedirs(self.save_dir, exist_ok=True)
            markdown = self.generate_markdown(
                file_name=file_name,
                size=input_data.size,
                language=input_data.language,
                content=content
            )

            # Replace the file extension (.pdf or .PDF) with .md
            markdown_file_path = os.path.join(self.save_dir, os.path.splitext(file_name)[0] + ".md")

            # Save the markdown content to a file in the output directory
            with open(markdown_file_path, "w") as f:
                f.write(markdown)

        # Post-process the content
        content = self.post_process(content)
        return content

    def parse(self, input_data: DocumentInput) -> str:
        """
        Parses the PDF file and returns the conversion results as markdown text.
        :param file_path: Path to the PDF file.
        :return: Markdown representation of the parsed content.
        """
        file_path = input_data.file_path
        language = input_data.language
        size = input_data.size

        if size > 2.0:
            logger.info(f"Parsing a large file of size {size}.")

            try:
                output: List[str] = self.parser_large.parse_and_export(
                    file_path,
                    **self.parser_options,
                    ocr_language=language
                    )
                return self.escape_markdown(output[0])
            except Exception as e:
                return f"Error parsing PDF file: {e}"


        try:
            output: List[str] = self.parser.parse_and_export(
                file_path, 
                **self.parser_options, 
                ocr_language=language
                )
            return self.escape_markdown(output[0])
        
        except Exception as e:
            return f"Error parsing PDF file: {e}"


    @staticmethod
    def escape_markdown(text: str) -> str:
        return text.replace("$", r"\$")


    @staticmethod
    def generate_front_matter(
        file_name: str,
        size: float,
        language: str
        ) -> str:
        front_matter = [
            "---",
            f"file_name: {file_name}",
            f"file_size: {size}",
            f"file_language: {language}",
            "---"
        ]
        return "\n".join(front_matter)


    def generate_markdown(
        self,
        file_name: str,
        size: float,
        language: str,
        content: str
        ) -> str:
        front_matter = self.generate_front_matter(
            file_name=file_name,
            size=size,
            language=language
        )
        return f"{front_matter}\n\n{content}"


    def run(
            self, 
            input_data: DocumentInput
            ) -> List[str]:
        """
        """
        content = self.parse_file(input_data)
        logger.info(f"Finished parsing file: {input_data.file_path}")
        chunks = self.chunk_file(content)
        logger.info(f"Finished chunking file: {input_data.file_path}")
        return chunks
