import csv

from app.modules.documents.extractors.base_extractor import BaseExtractor


class CsvExtractor(BaseExtractor):

    def extract(self, file_path: str) -> str:
        rows: list[str] = []

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)

            for row in reader:
                rows.append(" | ".join(row))

        return "\n".join(rows)
