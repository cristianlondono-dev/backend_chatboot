from docx import Document as DocxDocument

from app.modules.documents.extractors.base_extractor import BaseExtractor


class DocxExtractor(BaseExtractor):

    def extract(self, file_path: str) -> str:
        doc = DocxDocument(file_path)

        paragraphs = [
            p.text
            for p in doc.paragraphs
            if p.text.strip()
        ]

        return "\n".join(paragraphs)
