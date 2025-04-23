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
from docling_core.types.doc import ImageRefMode
from typing import Union, List, Generator, Optional, Literal
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

    def load_documents(self, paths: List[str]) -> Generator[ConversionResult, None, None]:
        """
        """
        if not self.initialized:
            raise ValueError("The Docling Parser has not been initialized.")

        yield from self.converter.convert_all(paths)

    def parse_and_export(
        self,
        paths: Union[str, List[str]],
        ocr_language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based",
        **kwargs,
    ) -> List[str]:
        """
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
                device=accelerator.get("device", AcceleratorDevice.AUTO),
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
        for _, result in enumerate(self.load_documents(paths)):
            if result.status == ConversionStatus.SUCCESS:
                md = result.document.export_to_markdown(
                    image_mode=ImageRefMode.PLACEHOLDER,
                )
                data.append(md)

            else:
                raise ValueError(f"Failed to parse the document: {result.errors}")
            
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        return data

    
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

    def load_documents(self, paths: List[str]) -> Generator[ConversionResult, None, None]:
        """
        """
        if not self.initialized:
            raise ValueError("The Docling Parser has not been initialized.")

        yield from self.converter.convert_all(paths)

    def parse_and_export(
        self,
        paths: Union[str, List[str]],
        ocr_language: Optional[Literal["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]] = "latin-based",
        **kwargs,
    ) -> List[str]:
        """
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
        for _, result in enumerate(self.load_documents(paths)):
            if result.status == ConversionStatus.SUCCESS:
                md = result.document.export_to_markdown(
                    image_mode=ImageRefMode.PLACEHOLDER,
                )
                data.append(md)

            else:
                raise ValueError(f"Failed to parse the document: {result.errors}")
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        return data
    
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
