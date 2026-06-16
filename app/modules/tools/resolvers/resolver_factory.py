from app.modules.tools.resolvers.base_resolver import BaseResolver
from app.modules.tools.resolvers.rest_api_resolver import RestApiResolver
from app.modules.tools.resolvers.google_sheets_resolver import GoogleSheetsResolver


class ResolverFactory:

    _registry: dict[str, type[BaseResolver]] = {
        "rest_api": RestApiResolver,
        "google_sheets": GoogleSheetsResolver,
    }

    @classmethod
    def create(cls, resolver_type: str, resolver_config: dict) -> BaseResolver:
        resolver_class = cls._registry.get(resolver_type)
        if resolver_class is None:
            raise ValueError(f"Unsupported resolver type: '{resolver_type}'. Supported: {list(cls._registry)}")
        return resolver_class(resolver_config)
