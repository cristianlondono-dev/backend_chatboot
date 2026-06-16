import httpx

from app.modules.tools.resolvers.base_resolver import BaseResolver
from app.core.logging.loggers import application_logger, error_logger


class RestApiResolver(BaseResolver):
    """
    Resolves user identity via a REST API endpoint.

    Expected resolver_config keys:
      url              - endpoint URL with {identifier} placeholder
      method           - HTTP method (default: GET)
      headers          - dict of request headers (optional)
      response_path    - dot-separated path to extract the user object (optional)
      canonical_field  - field name to use as the canonical user ID
    """

    def __init__(self, config: dict):
        self.url = config["url"]
        self.method = config.get("method", "GET").upper()
        self.headers = config.get("headers", {})
        self.response_path = config.get("response_path")
        self.canonical_field = config["canonical_field"]

    def resolve(self, identifier: str) -> dict | None:
        url = self.url.replace("{identifier}", identifier)
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.request(self.method, url, headers=self.headers)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            if self.response_path:
                for key in self.response_path.split("."):
                    data = data[key]

            application_logger.info(f"[resolver] REST API resolved identifier={identifier}")
            return data

        except httpx.HTTPStatusError as exc:
            error_logger.warning(f"[resolver] HTTP {exc.response.status_code} for identifier={identifier}: {exc}")
            return None
        except Exception as exc:
            error_logger.error(f"[resolver] Unexpected error for identifier={identifier}: {exc}", exc_info=True)
            return None
