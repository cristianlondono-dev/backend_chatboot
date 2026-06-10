import io
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings


class SupabaseStorageService:

    def __init__(self):
        from supabase import create_client
        self._client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self._bucket = settings.SUPABASE_BUCKET_NAME

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
