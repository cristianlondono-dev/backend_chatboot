from abc import ABC, abstractmethod


class BaseAction(ABC):
    """
    Abstract base for all executable chatbot actions.

    Subclasses declare:
      - ACTION_TYPE: unique string key registered in the ActionRegistry
      - DEFAULT_DESCRIPTION: default LLM-facing description
      - DEFAULT_PARAMETERS_SCHEMA: default JSON Schema for the function parameters

    The admin can override description and parameters_schema per ToolAction DB record.
    """

    ACTION_TYPE: str
    DEFAULT_DESCRIPTION: str
    DEFAULT_PARAMETERS_SCHEMA: dict

    def __init__(self, credentials: dict, config: dict):
        self.credentials = credentials
        self.config = config

    @abstractmethod
    async def execute(self, params: dict) -> dict:
        """
        Execute the action with the given params.

        Returns a dict that will be serialised to JSON and sent back to the LLM
        as a tool result message.

        Raise an exception on failure — the executor catches it and returns
        {"error": "..."} to the LLM so it can apologise gracefully.
        """
