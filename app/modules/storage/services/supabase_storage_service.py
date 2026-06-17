import io
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
from app.modules.storage.base_storage import BaseStorageService


class SupabaseStorageService(BaseStorageService):
    """
    Supabase Storage implementation.

    When credentials/config dicts are empty the service falls back to the
    global environment variables (SUPABASE_URL, SUPABASE_SERVICE_KEY,
    SUPABASE_BUCKET_NAME).

    Credentials keys (optional — override env vars):
      - url: str
      - service_key: str

    Config keys (optional):
      - bucket_name: str
    """

    def __init__(self, credentials: dict | None = None, config: dict | None = None):
        from supabase import create_client

        creds = credentials or {}
        cfg = config or {}

        url = creds.get("url") or settings.SUPABASE_URL
        key = creds.get("service_key") or settings.SUPABASE_SERVICE_KEY
        self._bucket = cfg.get("bucket_name") or settings.SUPABASE_BUCKET_NAME

        self._client = create_client(url, key)

    def upload(
        self,
        file_bytes: bytes,
        knowledge_base_id: UUID,
        file_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        timestamp = int(datetime.now(timezone.utc).timestamp())
        storage_path = f"{knowledge_base_id}/{timestamp}_{file_name}"

        self._client.storage.from_(self._bucket).upload(
            path=storage_path,
            file=io.BytesIO(file_bytes),
            file_options={"content-type": content_type, "upsert": "true"}
        )

        return self._client.storage.from_(self._bucket).get_public_url(storage_path)
