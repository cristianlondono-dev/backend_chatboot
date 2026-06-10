from pypdf import PdfReader

from app.modules.documents.extractors.base_extractor import BaseExtractor


class PdfExtractor(BaseExtractor):

    def extract(self, file_path: str) -> str:
        reader = PdfReader(file_path)

        parts = [
            page.extract_text()
            for page in reader.pages
            if page.extract_text()
        ]

        return "\n".join(parts)
