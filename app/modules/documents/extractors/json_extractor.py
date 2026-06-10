import json

from app.modules.documents.extractors.base_extractor import BaseExtractor


class JsonExtractor(BaseExtractor):

    def extract(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return json.dumps(data, ensure_ascii=False, indent=2)
