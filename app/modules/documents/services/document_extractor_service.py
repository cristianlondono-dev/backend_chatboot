from app.modules.documents.extractors.base_extractor import BaseExtractor
from app.modules.documents.extractors.csv_extractor import CsvExtractor
from app.modules.documents.extractors.docx_extractor import DocxExtractor
from app.modules.documents.extractors.json_extractor import JsonExtractor
from app.modules.documents.extractors.pdf_extractor import PdfExtractor
from app.modules.documents.extractors.xlsx_extractor import XlsxExtractor

_EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    "pdf": PdfExtractor(),
    "csv": CsvExtractor(),
    "docx": DocxExtractor(),
    "json": JsonExtractor(),
    "xlsx": XlsxExtractor(),
}

SUPPORTED_TYPES: frozenset[str] = frozenset(_EXTRACTOR_MAP.keys())


class DocumentExtractorService:

    def extract(self, file_path: str, file_type: str) -> str:
        extractor = _EXTRACTOR_MAP.get(file_type.lower())

        if extractor is None:
            raise ValueError(
                f"Unsupported file type '{file_type}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TYPES))}"
            )

        return extractor.extract(file_path)
