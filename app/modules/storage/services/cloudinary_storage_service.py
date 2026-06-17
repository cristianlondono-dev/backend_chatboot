import io
from datetime import datetime, timezone
from uuid import UUID

from app.modules.storage.base_storage import BaseStorageService


class CloudinaryStorageService(BaseStorageService):
    """
    Cloudinary storage implementation.

    Required credentials keys:
      - cloud_name: str
      - api_key: str
      - api_secret: str
    """

    def __init__(self, credentials: dict, config: dict):
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError as exc:
            raise ImportError(
                "cloudinary is required for Cloudinary storage. Install it with: pip install cloudinary"
            ) from exc

        cloudinary.config(
            cloud_name=credentials["cloud_name"],
            api_key=credentials["api_key"],
            api_secret=credentials["api_secret"],
        )
        self._folder = config.get("folder", "chatbot-documents")

    def upload(
        self,
        file_bytes: bytes,
        knowledge_base_id: UUID,
        file_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        import cloudinary.uploader

        timestamp = int(datetime.now(timezone.utc).timestamp())
        public_id = f"{self._folder}/{knowledge_base_id}/{timestamp}_{file_name}"

        result = cloudinary.uploader.upload(
            io.BytesIO(file_bytes),
            public_id=public_id,
            resource_type="raw",
        )
        return result["secure_url"]
