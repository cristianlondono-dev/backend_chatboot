import json

import gspread
from google.oauth2.service_account import Credentials

from app.modules.tools.resolvers.base_resolver import BaseResolver
from app.core.logging.loggers import application_logger, error_logger

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetsResolver(BaseResolver):
    """
    Resolves user identity against a Google Sheets spreadsheet.

    Expected resolver_config keys:
      spreadsheet_id     - the ID from the sheet URL
      sheet_name         - worksheet tab name (default: first sheet)
      identifier_column  - column header to search by (e.g. "celular")
      canonical_field    - column header to use as canonical user ID (e.g. "cedula")
      credentials_json   - service account credentials as a dict or JSON string
    """

    def __init__(self, config: dict):
        self.spreadsheet_id = config["spreadsheet_id"]
        self.sheet_name = config.get("sheet_name")
        self.identifier_column = config["identifier_column"]
        self.canonical_field = config["canonical_field"]

        creds_raw = config["credentials_json"]
        creds_dict = json.loads(creds_raw) if isinstance(creds_raw, str) else creds_raw
        self._credentials = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)

    def resolve(self, identifier: str) -> dict | None:
        try:
            client = gspread.authorize(self._credentials)

            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = (
                spreadsheet.worksheet(self.sheet_name)
                if self.sheet_name
                else spreadsheet.sheet1
            )

            records = worksheet.get_all_records()

            identifier_clean = identifier.strip().lower()
            for record in records:
                cell = str(record.get(self.identifier_column, "")).strip().lower()
                if cell == identifier_clean:
                    application_logger.info(
                        f"[resolver:sheets] Found identifier={identifier} "
                        f"in spreadsheet={self.spreadsheet_id}"
                    )
                    return record

            application_logger.info(
                f"[resolver:sheets] identifier={identifier} not found "
                f"in spreadsheet={self.spreadsheet_id}"
            )
            return None

        except gspread.exceptions.SpreadsheetNotFound:
            error_logger.error(f"[resolver:sheets] Spreadsheet not found: {self.spreadsheet_id}")
            return None
        except gspread.exceptions.WorksheetNotFound:
            error_logger.error(f"[resolver:sheets] Worksheet not found: {self.sheet_name}")
            return None
        except Exception as exc:
            error_logger.error(f"[resolver:sheets] Unexpected error: {exc}", exc_info=True)
            return None
