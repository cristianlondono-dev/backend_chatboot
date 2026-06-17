from abc import ABC, abstractmethod
from uuid import UUID


class BaseStorageService(ABC):

    @abstractmethod
    def upload(
        self,
        file_bytes: bytes,
        knowledge_base_id: UUID,
        file_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload a file and return its public URL."""
