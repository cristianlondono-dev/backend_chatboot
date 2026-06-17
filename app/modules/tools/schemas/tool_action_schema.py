from uuid import UUID
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal[
    # Shopify
    "shopify_get_order",
    "shopify_confirm_order",
    "shopify_list_orders",
    "shopify_cancel_order",
    # Google Calendar
    "google_calendar_create_event",
    "google_calendar_list_events",
    "google_calendar_cancel_event",
    "google_calendar_update_event",
    # Generic
    "custom_rest",
]


class CreateToolActionRequest(BaseModel):
    name: str = Field(
        description="Unique function name for this agent (used as OpenAI function name). "
                    "Only letters, numbers and underscores. Example: 'consultar_pedido'."
    )
    action_type: ActionType = Field(
        description="Built-in action type. Use 'custom_rest' for arbitrary HTTP endpoints."
    )
    description: str = Field(
        description="Plain-language description shown to the LLM so it knows when to call this action."
    )
    parameters_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema object describing the parameters the LLM must supply. "
                    "Leave empty to use the built-in defaults for the action_type."
    )
    credentials: dict | None = Field(
        default=None,
        description="Sensitive data: API tokens, OAuth credentials, etc. "
                    "See README for the required keys per action_type."
    )
    config: dict | None = Field(
        default=None,
        description="Non-sensitive settings: store URL, calendar ID, timezone, etc. "
                    "See README for the required keys per action_type."
    )


class UpdateToolActionRequest(BaseModel):
    name: str
    description: str
    parameters_schema: dict = Field(default_factory=dict)
    credentials: dict | None = None
    config: dict | None = None
    is_active: bool = True


class ToolActionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    action_type: str
    description: str
    parameters_schema: dict
    config: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestToolActionRequest(BaseModel):
    params: dict = Field(
        description="Parameters matching this action's parameters_schema."
    )


class TestToolActionResponse(BaseModel):
    success: bool
    result: dict | None = None
    error: str | None = None
