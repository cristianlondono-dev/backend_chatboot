import io
from datetime import datetime, timezone
from uuid import UUID

from app.modules.storage.base_storage import BaseStorageService


class S3StorageService(BaseStorageService):
    """
    AWS S3 storage implementation.

    Required config keys:
      - bucket: str
      - region: str  (e.g. "us-east-1")

    Required credentials keys:
      - access_key_id: str
      - secret_access_key: str
    """

    def __init__(self, credentials: dict, config: dict):
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for S3 storage. Install it with: pip install boto3"
            ) from exc

        self._bucket = config["bucket"]
        self._region = config.get("region", "us-east-1")
        self._client = boto3.client(
            "s3",
            region_name=self._region,
            aws_access_key_id=credentials["access_key_id"],
            aws_secret_access_key=credentials["secret_access_key"],
        )

    def upload(
        self,
        file_bytes: bytes,
        knowledge_base_id: UUID,
        file_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        timestamp = int(datetime.now(timezone.utc).timestamp())
        key = f"{knowledge_base_id}/{timestamp}_{file_name}"

        self._client.upload_fileobj(
            io.BytesIO(file_bytes),
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
        )

        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
