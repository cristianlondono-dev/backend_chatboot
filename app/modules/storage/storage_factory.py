from app.modules.storage.base_storage import BaseStorageService


def create_storage_service(
    provider: str,
    credentials: dict,
    config: dict
) -> BaseStorageService:
    """
    Factory that returns the right storage service for the given provider.

    Supported providers:
      - "supabase"    (default) — uses Supabase Storage
      - "s3"          — uses AWS S3
      - "cloudinary"  — uses Cloudinary

    For Supabase the credentials/config can be empty dicts to fall back
    to the global environment variables.
    """
    if provider == "supabase":
        from app.modules.storage.services.supabase_storage_service import SupabaseStorageService
        return SupabaseStorageService(credentials=credentials, config=config)

    if provider == "s3":
        from app.modules.storage.services.s3_storage_service import S3StorageService
        return S3StorageService(credentials=credentials, config=config)

    if provider == "cloudinary":
        from app.modules.storage.services.cloudinary_storage_service import CloudinaryStorageService
        return CloudinaryStorageService(credentials=credentials, config=config)

    raise ValueError(
        f"Unknown storage provider '{provider}'. "
        "Supported values: 'supabase', 's3', 'cloudinary'."
    )


def create_default_storage_service() -> BaseStorageService:
    """Returns the default Supabase storage service using env variables."""
    from app.modules.storage.services.supabase_storage_service import SupabaseStorageService
    return SupabaseStorageService(credentials={}, config={})
