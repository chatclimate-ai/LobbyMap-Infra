from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
    AcceleratorOptions,
    TableStructureOptions,
    AcceleratorDevice
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling_core.types.doc import ImageRefMode, DoclingDocument
from typing import Union, List, Generator, Dict, Optional, Literal
from .schemas import ParserOutput
import sys
import torch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DoclingParserLarge:
    """
    Parse a large PDF file using the Docling Parser
    """

    def __init__(self):
        self.initialized = False

    def __initialize_docling(
        self,
        pipeline_options: PdfPipelineOptions,
        backend: Union[DoclingParseDocumentBackend, PyPdfiumDocumentBackend],
    ) -> None:
        """
        Initialize the DocumentConverter with the given pipeline options and backend.

        Args:
            pipeline_options (PdfPipelineOptions): The pipeline options to use for parsing the document
            backend (Union[DoclingParseDocumentBackend, PyPdfiumDocumentBackend]): The backend to use for parsing the document
        
        Returns:
            None
        """
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=backend
                )
            },
        )

        self.initialized = True

    def load_documents(
        self, paths: List[str], **kwargs
    ) -> Generator[ConversionResult, None, None]:
        """
        Load the given documents and parse them. The documents are parsed in parallel.

        Args:
            paths (List[str]): The list of paths to the documents to parse
            raises_on_error (bool): Whether to raise an error if the document fails to parse. Default is True
            max_num_pages (int): The maximum number of pages to parse. If the document has more pages, it will be skipped. Default is sys.maxsize
            max_file_size (int): The maximum file size to parse. If the document is larger, it will be skipped. Default is sys.maxsize
        
        Returns:
            conversion_result (Generator[ConversionResult, None, None]): A generator that yields the parsed result for each document (file)

        Raises:
            ValueError: If the Docling Parser has not been initialized
        
        Examples:
            >>> parser = DoclingPDFParser()
            >>> for result in parser.load_documents(["path/to/file1.pdf", "path/to/file2.pdf"]):
            ...     if result.status == ConversionStatus.SUCCESS:
            ...         print(result.document)
            ...     else:
            ...         print(result.errors)
            ConversionResult(status=<ConversionStatus.SUCCESS: 'SUCCESS'>, document=<DoclingDocument>, errors=None)
        """
        if not self.initialized:
            raise ValueError("The Docling Parser has not been initialized.")

        raises_on_error = kwargs.get("raises_on_error", True)
        max_num_pages = kwargs.get("max_num_pages", sys.maxsize)
        max_file_size = kwargs.get("max_file_size", sys.maxsize)

        yield from self.converter.convert_all(
            paths,
            raises_on_error=raises_on_error,
            max_num_pages=max_num_pages,
            max_file_size=max_file_size,
        )

    def parse_and_export(
        self,
        paths: Union[str, List[str]],
        modalities: List[str] = ["text", "tables", "images"],
        ocr_language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based",
        **kwargs,
    ) -> List[ParserOutput]:
        """
        Parse the given documents and export the parsed results in the specified modalities. The parsed results are exported as a ParserOutput object.

        Args:
            paths (Union[str, List[str]): The path(s) to the document(s) to parse
            modalities (List[str]): The modalities to export the parsed results in (text, tables, images). Default is ["text", "tables", "images"]
            do_ocr (bool): Whether to perform OCR on the document. Default is True.
            ocr_options (str): The OCR options to use (easyocr, tesseract). Default is easyocr.
            do_table_structure (bool): Whether to extract table structure from the document. Default is True.
            do_cell_matching (bool): Whether to perform cell matching on the tables. Default is False.
            tableformer_mode (str): The mode to use for extracting table structure (ACCURATE, FAST). Default is ACCURATE.
            images_scale (float): The scale factor to apply to the images. Default is 1.0.
            generate_page_images (bool): Whether to generate images for each page. Default is False.
            generate_picture_images (bool): Whether to generate images for pictures. Default is True.
            generate_table_images (bool): Whether to generate images for tables. Default is True.
            backend (str): The backend to use for parsing the document (docling, pypdfium). Default is docling.
            embed_images (bool): Whether to embed images in the exported text (markdown string). Default is True.

        Returns:
            data (List[ParserOutput]): A list of parsed results for the document(s)

        Raises:
            ValueError: If the OCR options specified are invalid
            ValueError: If the mode specified for the tableformer is invalid
            ValueError: If the backend specified is invalid
        
        Examples:
            >>> parser = DoclingPDFParser()
            >>> data = parser.parse_and_export("path/to/file.pdf", modalities=["text", "tables", "images"])
            >>> print(data)
            [ParserOutput(text="...", tables=[{"table_md": "...", "table_df": pd.DataFrame}], images=[{"image": Image.Image}])]
        """
        if isinstance(paths, str):
            paths = [paths]

        if not self.initialized:
            logging.info(f"Docling not intialized. Initializing with Large File settings")
            # Set pipeline options
            pipeline_options = PdfPipelineOptions()

            # device settings
            accelerator: dict = kwargs.get("accelerator", {})
            accelerator_options = AcceleratorOptions(
                num_threads=accelerator.get("num_threads", 8),
                device=accelerator.get("device", AcceleratorDevice.CUDA),
            )
            pipeline_options.accelerator_options = accelerator_options

            # Set ocr options
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = EasyOcrOptions(
                force_full_page_ocr= False,
                lang=self.map_language(ocr_language)
                )
            

            # Set table structure options
            pipeline_options.do_table_structure = True

            pipeline_options.table_structure_options = TableStructureOptions(
                do_cell_matching= False,
                tableformer_mode= "fast"
            )
            
            # Set image options
            pipeline_options.images_scale = 1.0
            pipeline_options.generate_page_images = False
            pipeline_options.generate_picture_images = False

            # Set backend
            backend = PyPdfiumDocumentBackend

            # Initialize the Docling Parser
            self.__initialize_docling(pipeline_options, backend)
        
        else:
            logging.info(f"Docling already intialized with Large File settings")

        data = []
        for i, result in enumerate(self.load_documents(paths, **kwargs)):
            if result.status == ConversionStatus.SUCCESS:
                output = self.__export_result(result.document, modalities)
                data.append(output)

            else:
                raise ValueError(f"Failed to parse the document: {result.errors}")
            
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        return data

    def __export_result(
        self, document: DoclingDocument, modalities: List[str]
    ) -> ParserOutput:
        """
        Export the parsed results in a ParserOutput object for the given document.

        Args:
            document (DoclingDocument): The document to export
            modalities (List[str]): The modalities to export the parsed results in (text, tables, images)
        
        Returns:
            output (ParserOutput): The parsed results for the document
        """
        text = ""
        tables: List[Dict] = []
        images: List[Dict] = []

        if "text" in modalities:
            text = self._extract_text(document)

        return ParserOutput(text=text, tables=tables, images=images)



    def _extract_text(self, item: DoclingDocument) -> str:
        """
        Extract text from the document and return as a markdown string.

        Args:
            item (DoclingDocument): The document to extract text from
        
        Returns:
            text (str): The text extracted from the document as a markdown string. If embed_images is True, the images are embedded in the text. Otherwise, the images are replaced with the image placeholder (<!-- image -->).
        """
        return item.export_to_markdown(
            image_mode=ImageRefMode.PLACEHOLDER,
        )
    
    @staticmethod
    def map_language(language:str) -> List[str]:
        if language == "latin-based":
            return [
                "af",
                "az",
                "bs",
                "cs",
                "cy",
                "da",
                "de",
                "en",
                "es",
                "et",
                "fr",
                "ga",
                "hr",
                "hu",
                "id",
                "is",
                "it",
                "ku",
                "la",
                "lt",
                "lv",
                "mi",
                "ms",
                "mt",
                "nl",
                "no",
                "oc",
                "pi",
                "pl",
                "pt",
                "ro",
                "rs_latin",
                "sk",
                "sl",
                "sq",
                "sv",
                "sw",
                "tl",
                "tr",
                "uz",
                "vi"
            ]
        elif language == "arabic-based":
            return [
                "ar",
                "fa",
                "ug",
                "ur",
                "en"

                ]
        elif language == "bengali-based":
            return [
                "as",
                "bn",
                "en"
            ]
        elif language == "cyrillic-based":
            return [
                "ru",
                "rs_cyrillic",
                "be",
                "bg",
                "uk",
                "mn",
                "abq",
                "ady",
                "kbd",
                "ava",
                "dar",
                "inh",
                "che",
                "lbe",
                "lez",
                "tab",
                "tjk",
                "en"
            ]
     
        elif language == "devanagari-based":
            return [
                "hi",
                "mr",
                "ne",
                "bh",
                "mai",
                "ang",
                "bho",
                "mah",
                "sck",
                "new",
                "gom",
                "en"
            ]
        
        elif language == "chinese-traditional":
            return [
                "ch_tra",
                "en"
            ]

        elif language == "chinese-simplified":
            return [
                "ch_sim",
                "en"
            ]
        
        elif language == "japanese":
            return [
                "ja",
                "en"
            ]
        
        elif language == "korean":
            return [
                "ko",
                "en"
            ]
        
        elif language == "kannada":
            return [
                "kn",
                "en"
            ]
        
        elif language == "telugu":
            return [
                "te",
                "en"
            ]
        
        elif language == "thai":
            return [
                "th",
                "en"
            ]
        else:
            return [
                "en"
            ]





class DoclingPDFParser:
    """
    Parse a PDF file using the Docling Parser
    """

    def __init__(self):
        self.initialized = False

    def __initialize_docling(
        self,
        pipeline_options: PdfPipelineOptions,
        backend: Union[DoclingParseDocumentBackend, PyPdfiumDocumentBackend],
    ) -> None:
        """
        Initialize the DocumentConverter with the given pipeline options and backend.

        Args:
            pipeline_options (PdfPipelineOptions): The pipeline options to use for parsing the document
            backend (Union[DoclingParseDocumentBackend, PyPdfiumDocumentBackend]): The backend to use for parsing the document
        
        Returns:
            None
        """
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, backend=backend
                )
            },
        )

        self.initialized = True

    def load_documents(
        self, paths: List[str], **kwargs
    ) -> Generator[ConversionResult, None, None]:
        """
        Load the given documents and parse them. The documents are parsed in parallel.

        Args:
            paths (List[str]): The list of paths to the documents to parse
            raises_on_error (bool): Whether to raise an error if the document fails to parse. Default is True
            max_num_pages (int): The maximum number of pages to parse. If the document has more pages, it will be skipped. Default is sys.maxsize
            max_file_size (int): The maximum file size to parse. If the document is larger, it will be skipped. Default is sys.maxsize
        
        Returns:
            conversion_result (Generator[ConversionResult, None, None]): A generator that yields the parsed result for each document (file)

        Raises:
            ValueError: If the Docling Parser has not been initialized
        
        Examples:
            >>> parser = DoclingPDFParser()
            >>> for result in parser.load_documents(["path/to/file1.pdf", "path/to/file2.pdf"]):
            ...     if result.status == ConversionStatus.SUCCESS:
            ...         print(result.document)
            ...     else:
            ...         print(result.errors)
            ConversionResult(status=<ConversionStatus.SUCCESS: 'SUCCESS'>, document=<DoclingDocument>, errors=None)
        """
        if not self.initialized:
            raise ValueError("The Docling Parser has not been initialized.")

        raises_on_error = kwargs.get("raises_on_error", True)
        max_num_pages = kwargs.get("max_num_pages", sys.maxsize)
        max_file_size = kwargs.get("max_file_size", sys.maxsize)

        yield from self.converter.convert_all(
            paths,
            raises_on_error=raises_on_error,
            max_num_pages=max_num_pages,
            max_file_size=max_file_size,
        )

    def parse_and_export(
        self,
        paths: Union[str, List[str]],
        modalities: List[str] = ["text", "tables", "images"],
        ocr_language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based",
        **kwargs,
    ) -> List[ParserOutput]:
        """
        Parse the given documents and export the parsed results in the specified modalities. The parsed results are exported as a ParserOutput object.

        Args:
            paths (Union[str, List[str]): The path(s) to the document(s) to parse
            modalities (List[str]): The modalities to export the parsed results in (text, tables, images). Default is ["text", "tables", "images"]
            do_ocr (bool): Whether to perform OCR on the document. Default is True.
            ocr_options (str): The OCR options to use (easyocr, tesseract). Default is easyocr.
            do_table_structure (bool): Whether to extract table structure from the document. Default is True.
            do_cell_matching (bool): Whether to perform cell matching on the tables. Default is False.
            tableformer_mode (str): The mode to use for extracting table structure (ACCURATE, FAST). Default is ACCURATE.
            images_scale (float): The scale factor to apply to the images. Default is 1.0.
            generate_page_images (bool): Whether to generate images for each page. Default is False.
            generate_picture_images (bool): Whether to generate images for pictures. Default is True.
            generate_table_images (bool): Whether to generate images for tables. Default is True.
            backend (str): The backend to use for parsing the document (docling, pypdfium). Default is docling.
            embed_images (bool): Whether to embed images in the exported text (markdown string). Default is True.

        Returns:
            data (List[ParserOutput]): A list of parsed results for the document(s)

        Raises:
            ValueError: If the OCR options specified are invalid
            ValueError: If the mode specified for the tableformer is invalid
            ValueError: If the backend specified is invalid
        
        Examples:
            >>> parser = DoclingPDFParser()
            >>> data = parser.parse_and_export("path/to/file.pdf", modalities=["text", "tables", "images"])
            >>> print(data)
            [ParserOutput(text="...", tables=[{"table_md": "...", "table_df": pd.DataFrame}], images=[{"image": Image.Image}])]
        """
        if isinstance(paths, str):
            paths = [paths]

        if not self.initialized:
            logging.info(f"Docling not intialized. Initializing with Small File settings")
            # Set pipeline options
            pipeline_options = PdfPipelineOptions()

            # device settings
            accelerator: dict = kwargs.get("accelerator", {})
            accelerator_options = AcceleratorOptions(
                num_threads=accelerator.get("num_threads", 8),
                device=accelerator.get("device", AcceleratorDevice.CUDA),
            )
            pipeline_options.accelerator_options = accelerator_options

            # Set ocr options
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = EasyOcrOptions(
                force_full_page_ocr=True, 
                lang=self.map_language(ocr_language)
                )
           

            # Set table structure options
            pipeline_options.do_table_structure = True

            pipeline_options.table_structure_options = TableStructureOptions(
                do_cell_matching=False,
                tableformer_mode="accurate"
            )
            
            # Set image options
            pipeline_options.images_scale = 1.0
            pipeline_options.generate_page_images = False
            pipeline_options.generate_picture_images = False

            # Set backend
            backend = DoclingParseDocumentBackend

            # Initialize the Docling Parser
            self.__initialize_docling(pipeline_options, backend)
        
        else:
            logging.info(f"Docling already intialized with Small File settings")

        data = []
        for i, result in enumerate(self.load_documents(paths, **kwargs)):
            if result.status == ConversionStatus.SUCCESS:
                output = self.__export_result(result.document, modalities)
                data.append(output)

            else:
                raise ValueError(f"Failed to parse the document: {result.errors}")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        return data

    def __export_result(
        self, document: DoclingDocument, modalities: List[str]
    ) -> ParserOutput:
        """
        Export the parsed results in a ParserOutput object for the given document.

        Args:
            document (DoclingDocument): The document to export
            modalities (List[str]): The modalities to export the parsed results in (text, tables, images)
        
        Returns:
            output (ParserOutput): The parsed results for the document
        """
        text = ""
        tables: List[Dict] = []
        images: List[Dict] = []

        if "text" in modalities:
            text = self._extract_text(document)

        return ParserOutput(text=text, tables=tables, images=images)


    def _extract_text(self, item: DoclingDocument) -> str:
        """
        Extract text from the document and return as a markdown string.

        Args:
            item (DoclingDocument): The document to extract text from
        
        Returns:
            text (str): The text extracted from the document as a markdown string. The images are replaced with the image placeholder (<!-- image -->).
        """

        return item.export_to_markdown(
            image_mode=ImageRefMode.PLACEHOLDER,
        )
    
    @staticmethod
    def map_language(language:str) -> List[str]:
        if language == "latin-based":
            return [
                "af",
                "az",
                "bs",
                "cs",
                "cy",
                "da",
                "de",
                "en",
                "es",
                "et",
                "fr",
                "ga",
                "hr",
                "hu",
                "id",
                "is",
                "it",
                "ku",
                "la",
                "lt",
                "lv",
                "mi",
                "ms",
                "mt",
                "nl",
                "no",
                "oc",
                "pi",
                "pl",
                "pt",
                "ro",
                "rs_latin",
                "sk",
                "sl",
                "sq",
                "sv",
                "sw",
                "tl",
                "tr",
                "uz",
                "vi"
            ]
        elif language == "arabic-based":
            return [
                "ar",
                "fa",
                "ug",
                "ur",
                "en"

                ]
        elif language == "bengali-based":
            return [
                "as",
                "bn",
                "en"
            ]
        elif language == "cyrillic-based":
            return [
                "ru",
                "rs_cyrillic",
                "be",
                "bg",
                "uk",
                "mn",
                "abq",
                "ady",
                "kbd",
                "ava",
                "dar",
                "inh",
                "che",
                "lbe",
                "lez",
                "tab",
                "tjk",
                "en"
            ]
     
        elif language == "devanagari-based":
            return [
                "hi",
                "mr",
                "ne",
                "bh",
                "mai",
                "ang",
                "bho",
                "mah",
                "sck",
                "new",
                "gom",
                "en"
            ]
        
        elif language == "chinese-traditional":
            return [
                "ch_tra",
                "en"
            ]

        elif language == "chinese-simplified":
            return [
                "ch_sim",
                "en"
            ]
        
        elif language == "japanese":
            return [
                "ja",
                "en"
            ]
        
        elif language == "korean":
            return [
                "ko",
                "en"
            ]
        
        elif language == "kannada":
            return [
                "kn",
                "en"
            ]
        
        elif language == "telugu":
            return [
                "te",
                "en"
            ]
        
        elif language == "thai":
            return [
                "th",
                "en"
            ]
        else:
            return [
                "en"
            ]
