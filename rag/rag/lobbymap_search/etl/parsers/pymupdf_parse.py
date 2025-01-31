import fitz  # PyMuPDF
from PIL import Image
from typing import Union, List, Generator, Dict, Tuple
from io import BytesIO
from .schemas import ParserOutput
from fitz import Page

class PyMuPDFParser:
    """
    Parse a PDF file using PyMuPDF
    """

    def __init__(self):
        pass

    def load_document(self, paths : Union[str, List[str]]) -> Generator[List[Page], None, None]:
        for path in paths:
            with fitz.open(path) as doc:
                pages = [doc.load_page(page_num) for page_num in range(doc.page_count)]
                yield pages


    def parse_and_export(self, paths : Union[str, List[str]], modalities : List[str] = ["text", "tables", "images"], **kwargs) -> List[ParserOutput]:
        """
        Parse the given document and export the parsed results.
        """
        if isinstance(paths, str):
            paths = [paths]
        data = []
        for result in self.load_document(paths):
            output = self.__export_result(result, modalities)

            data.append(output)
           
        return data

    
    def __export_result(self, pages: List[Page], modalities: List[str]) -> ParserOutput:
        """
        Export the parsed result to a list of dictionaries containing text, tables, and images.
        """
        text = ""
        tables: List[Dict] = []
        images: List[Dict] = []

        for page in pages:
            if "text" in modalities:
                text += self._extract_text(page) + "\n"
            
            if "tables" in modalities:
                tables += self._extract_tables(page)
            
            if "images" in modalities:
                images += self._extract_images(page)
        
        return ParserOutput(
            text=text,
            tables=tables,
            images=images
        )


    def _extract_text(self, page: Page) -> str:
        """
        Extract text from a page.
        """
        return page.get_text("text")

    def _extract_images(self, page: Page) -> List[Dict]:
        """
        Extract images from a page and return as a list of dictionaries with image and caption data.
        """
        images = []
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            img_data = BytesIO(base_image["image"])
            image = Image.open(img_data).convert('RGB')
            images.append({"image": image})
        return images

    def _extract_tables(self, page: Page) -> List[Dict]:
        tabs = page.find_tables()

        tables = []
        for tab in tabs:
            tables.append({
                "table_md": tab.to_markdown(),
                "table_df": tab.to_pandas()
            })
            
        return  tables
