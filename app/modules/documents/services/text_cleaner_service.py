import re


class TextCleanerService:

    def clean(
        self,
        text: str
    ) -> str:

        text = re.sub(r'\s+', ' ', text)

        return text.strip()