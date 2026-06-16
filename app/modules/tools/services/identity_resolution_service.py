from app.modules.tools.models.agent_tool_model import AgentTool
from app.modules.tools.resolvers.resolver_factory import ResolverFactory


class IdentityResolutionService:
    """
    Resolves a channel identifier to a canonical user ID and profile memories.

    For internal users: calls the configured resolver. Returns None if not found
    (caller must deny access).
    For external users: no resolution needed — channel_id IS the canonical ID.
    """

    def resolve(self, tool: AgentTool, channel_id: str) -> dict | None:
        """
        Returns:
          {
            "canonical_id": str,
            "memories": [{"memory": str, "importance": str}, ...]
          }
          or None if the user is not found (internal only).
        """
        if tool.user_type == "external":
            return {"canonical_id": channel_id, "memories": []}

        # Internal: resolver is mandatory
        if tool.resolver_type == "none" or not tool.resolver_config:
            return None

        resolver = ResolverFactory.create(tool.resolver_type, tool.resolver_config)
        data = resolver.resolve(channel_id)

        if data is None:
            return None

        canonical_id = str(data.get(resolver.canonical_field, channel_id))
        memories = self._apply_field_mapping(data, tool.field_mapping or {})

        return {"canonical_id": canonical_id, "memories": memories}

    @staticmethod
    def _apply_field_mapping(data: dict, field_mapping: dict) -> list[dict]:
        memories = []
        for field, template in field_mapping.items():
            value = data.get(field)
            if value is not None:
                memories.append({
                    "memory": template.replace("{value}", str(value)),
                    "importance": "high"
                })
        return memories
