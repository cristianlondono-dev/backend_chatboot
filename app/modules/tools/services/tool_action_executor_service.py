from app.core.logging.loggers import application_logger, error_logger
from app.modules.tools.actions.action_registry import ActionRegistry
from app.modules.tools.models.tool_action_model import ToolAction


class ToolActionExecutorService:
    """
    Executes a ToolAction given its DB record and the call-time parameters
    supplied by the LLM.

    Responsible for:
      - Instantiating the right action via the ActionRegistry
      - Calling execute()
      - Returning a result dict (or an error dict) to be sent back to the LLM
    """

    async def execute(self, tool_action: ToolAction, params: dict) -> dict:
        action_type = tool_action.action_type
        credentials = tool_action.credentials or {}
        config = tool_action.config or {}

        application_logger.info(
            f"[tool-action] Executing '{tool_action.name}' (type={action_type}) | params={params}"
        )

        try:
            action = ActionRegistry.create(action_type, credentials, config)
            result = await action.execute(params)
            application_logger.info(
                f"[tool-action] '{tool_action.name}' succeeded | keys={list(result.keys())}"
            )
            return result
        except Exception as exc:
            error_logger.error(
                f"[tool-action] '{tool_action.name}' failed: {type(exc).__name__}: {exc}",
                exc_info=True
            )
            return {"error": str(exc)}
