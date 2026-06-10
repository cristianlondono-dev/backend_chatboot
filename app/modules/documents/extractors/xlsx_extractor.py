import openpyxl

from app.modules.documents.extractors.base_extractor import BaseExtractor


class XlsxExtractor(BaseExtractor):

    def extract(self, file_path: str) -> str:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        rows: list[str] = []

        for sheet in wb.worksheets:
            rows.append(f"[Hoja: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(cell) if cell is not None else "" for cell in row]
                if any(cells):
                    rows.append(" | ".join(cells))

        wb.close()
        return "\n".join(rows)
