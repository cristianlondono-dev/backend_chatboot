from app.modules.tools.actions.base_action import BaseAction
from app.modules.tools.actions.shopify.get_order_action import ShopifyGetOrderAction
from app.modules.tools.actions.shopify.confirm_order_action import ShopifyConfirmOrderAction
from app.modules.tools.actions.shopify.list_orders_action import ShopifyListOrdersAction
from app.modules.tools.actions.shopify.cancel_order_action import ShopifyCancelOrderAction
from app.modules.tools.actions.google_calendar.create_event_action import GoogleCalendarCreateEventAction
from app.modules.tools.actions.google_calendar.list_events_action import GoogleCalendarListEventsAction
from app.modules.tools.actions.google_calendar.cancel_event_action import GoogleCalendarCancelEventAction
from app.modules.tools.actions.google_calendar.update_event_action import GoogleCalendarUpdateEventAction
from app.modules.tools.actions.custom_rest.custom_rest_action import CustomRestAction

_REGISTRY: dict[str, type[BaseAction]] = {
    # ── Shopify ──────────────────────────────────────────────────────────────
    ShopifyGetOrderAction.ACTION_TYPE: ShopifyGetOrderAction,
    ShopifyConfirmOrderAction.ACTION_TYPE: ShopifyConfirmOrderAction,
    ShopifyListOrdersAction.ACTION_TYPE: ShopifyListOrdersAction,
    ShopifyCancelOrderAction.ACTION_TYPE: ShopifyCancelOrderAction,
    # ── Google Calendar ──────────────────────────────────────────────────────
    GoogleCalendarCreateEventAction.ACTION_TYPE: GoogleCalendarCreateEventAction,
    GoogleCalendarListEventsAction.ACTION_TYPE: GoogleCalendarListEventsAction,
    GoogleCalendarCancelEventAction.ACTION_TYPE: GoogleCalendarCancelEventAction,
    GoogleCalendarUpdateEventAction.ACTION_TYPE: GoogleCalendarUpdateEventAction,
    # ── Generic ──────────────────────────────────────────────────────────────
    CustomRestAction.ACTION_TYPE: CustomRestAction,
}


class ActionRegistry:

    @staticmethod
    def create(action_type: str, credentials: dict, config: dict) -> BaseAction:
        cls = _REGISTRY.get(action_type)
        if not cls:
            raise ValueError(
                f"Unknown action_type '{action_type}'. "
                f"Available: {list(_REGISTRY.keys())}"
            )
        return cls(credentials=credentials, config=config)

    @staticmethod
    def get_defaults(action_type: str) -> dict:
        """Return the default description and parameters_schema for a built-in action_type."""
        cls = _REGISTRY.get(action_type)
        if not cls:
            return {}
        return {
            "description": cls.DEFAULT_DESCRIPTION,
            "parameters_schema": cls.DEFAULT_PARAMETERS_SCHEMA,
        }

    @staticmethod
    def list_types() -> list[str]:
        return list(_REGISTRY.keys())
