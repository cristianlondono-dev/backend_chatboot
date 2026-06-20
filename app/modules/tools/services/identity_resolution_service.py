from app.modules.tools.models.agent_tool_model import AgentTool
from app.modules.tools.resolvers.resolver_factory import ResolverFactory

_GIVEN_NAME_FIELDS = ("nombre", "nombres", "name", "first_name", "given_name")


class IdentityResolutionService:
    """
    Resolves a channel identifier to a canonical user ID and profile memories.

    For internal users: calls the configured resolver. Returns None if not found
    (caller must deny access).
    For external users: no resolution needed — channel_id IS the canonical ID.

    Every column returned by the resolver becomes a memory automatically
    ("Columna: valor"). field_mapping is only needed to override the wording
    for specific columns — it's no longer required to "unlock" a column.
    """

    def resolve(self, tool: AgentTool, channel_id: str) -> dict | None:
        """
        Returns:
          {
            "canonical_id": str,
            "memories": [{"memory": str, "importance": str}, ...],
            "given_name": str | None   # value of a "Nombre"-like column, for the nickname flow
          }
          or None if the user is not found (internal only).
        """
        if tool.user_type == "external":
            return {"canonical_id": channel_id, "memories": [], "given_name": None}

        # Internal: resolver is mandatory
        if tool.resolver_type == "none" or not tool.resolver_config:
            return None

        resolver = ResolverFactory.create(tool.resolver_type, tool.resolver_config)
        data = resolver.resolve(channel_id)

        if data is None:
            return None

        canonical_id = str(data.get(resolver.canonical_field, channel_id))
        memories = self._apply_field_mapping(data, tool.field_mapping or {})
        given_name = self._extract_given_name(data)

        return {"canonical_id": canonical_id, "memories": memories, "given_name": given_name}

    @staticmethod
    def _extract_given_name(data: dict) -> str | None:
        lowered = {str(k).strip().lower(): v for k, v in data.items()}
        for field in _GIVEN_NAME_FIELDS:
            value = lowered.get(field)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _apply_field_mapping(data: dict, field_mapping: dict) -> list[dict]:
        memories = []
        mapped_fields = set(field_mapping.keys())

        for field, template in field_mapping.items():
            value = data.get(field)
            if value is not None:
                memories.append({
                    "memory": template.replace("{value}", str(value)),
                    "importance": "high",
                    "field": field
                })

        # Any column not explicitly mapped still becomes a memory, using the
        # column header itself as the label — so resolvers don't require a
        # field_mapping entry per column to be picked up.
        for field, value in data.items():
            if field in mapped_fields:
                continue
            if value is None or str(value).strip() == "":
                continue
            memories.append({
                "memory": f"{field}: {value}",
                "importance": "high",
                "field": field
            })

        return memories
