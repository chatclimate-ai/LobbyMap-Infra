from typing import Literal, List
from .schemas import PdfDocument, DocumentInput
from .parsers.docling_parse import DoclingPDFParser
from .parsers.pymupdf_parse import PyMuPDFParser
from .parsers.schemas import ParserOutput
import os

class PDFParser:
    """
    PDFParser class for parsing PDF files.
    """

    def __init__(
            self, 
            parser: Literal["docling", "pymupdf"] = "docling",
            parser_options: dict = {},
            save_locally: bool = False, 
            save_dir: str = "output",
            ):
        """
        Initializes the PDFParser object.
        """
        if parser == "docling":
            self.parser = DoclingPDFParser()
        elif parser == "pymupdf":
            self.parser = PyMuPDFParser()
        else:
            raise ValueError(f"Invalid parser specified: {parser}")

        self.save_locally = save_locally
        self.save_dir = save_dir
        self.parser_options = parser_options



    def parse_file(
            self, 
            input_data: DocumentInput,
            ) -> PdfDocument:
        """
        """
        # Parse the PDF file and extract text content
        content = self.parse(input_data)

        # Extract file_name from the file_path
        file_name = os.path.basename(input_data.file_path)

        # Create a PdfDocument instance with the parsed content
        document = PdfDocument(
            file_name=file_name,
            content=content, 
            **input_data.metadata.model_dump()
            )

        # Save the parsed content to a markdown file
        if self.save_locally:
            os.makedirs(self.save_dir, exist_ok=True)
            markdown = self.generate_markdown(document)

            # Replace the file extension (.pdf or .PDF) with .md
            markdown_file_path = os.path.join(self.save_dir, os.path.splitext(file_name)[0] + ".md")

            # Save the markdown content to a file in the output directory
            with open(markdown_file_path, "w") as f:
                f.write(markdown)

        return document

    def parse(self, input_data: DocumentInput) -> str:
        """
        Parses the PDF file and returns the conversion results as markdown text.
        :param file_path: Path to the PDF file.
        :return: Markdown representation of the parsed content.
        """
        file_path = input_data.file_path
        language = input_data.metadata

        size = input_data.metadata.size

        if size > 5.0:
            large_file_options = self.parser_options
            large_file_options["ocr"]["easyocr_settings"]["force_full_page_ocr"] = False

            large_file_options["table"]["table_structure_options"]["tableformer_mode"] = "fast"

            large_file_options["backend"] = "pypdfium"

            try:
                output: List[ParserOutput] = self.parser.parse_and_export(
                    file_path, 
                    modalities=["text"], 
                    **large_file_options,
                    ocr_language=language
                    )
                return self.escape_markdown(output[0].text)
            except Exception as e:
                return f"Error parsing PDF file: {e}"


        try:
            output: List[ParserOutput] = self.parser.parse_and_export(file_path, modalities=["text"], **self.parser_options, ocr_language=language)
            return self.escape_markdown(output[0].text)
        except Exception as e:
            return f"Error parsing PDF file: {e}"


    @staticmethod
    def escape_markdown(text: str) -> str:
        return text.replace("$", r"\$")


    @staticmethod
    def generate_front_matter(pdf_document: PdfDocument) -> str:
        front_matter = [
            "---",
            f"file_name: {pdf_document.file_name}",
            f"author: {pdf_document.author or ''}",
            f"date: {pdf_document.date}",
            f"region: {pdf_document.region}",
            f"file_size: {pdf_document.size}",
            "---"
        ]
        return "\n".join(front_matter)


    @staticmethod
    def generate_markdown(pdf_document: PdfDocument) -> str:
        front_matter = PDFParser.generate_front_matter(pdf_document)
        return f"{front_matter}\n\n{pdf_document.content}"




