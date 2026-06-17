import httpx

from app.modules.tools.actions.base_action import BaseAction

_SHOPIFY_API_VERSION = "2024-01"

_VALID_REASONS = {"customer", "fraud", "inventory", "declined", "other"}


class ShopifyCancelOrderAction(BaseAction):
    """
    Cancels an open order in Shopify and optionally issues a refund.

    Required credentials:
      - access_token: str

    Required config:
      - store_url: str
    """

    ACTION_TYPE = "shopify_cancel_order"
    DEFAULT_DESCRIPTION = (
        "Cancela un pedido en Shopify. "
        "Úsalo cuando el cliente solicite cancelar su pedido. "
        "Si el pedido ya fue enviado, no puede cancelarse."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "ID numérico del pedido a cancelar."
            },
            "reason": {
                "type": "string",
                "enum": ["customer", "fraud", "inventory", "declined", "other"],
                "description": "Motivo de la cancelación (default: 'customer')."
            },
            "refund": {
                "type": "boolean",
                "description": "Si se debe emitir un reembolso al cancelar (default: true)."
            }
        },
        "required": ["order_id"]
    }

    async def execute(self, params: dict) -> dict:
        store_url = self.config.get("store_url", "").rstrip("/")
        access_token = self.credentials.get("access_token", "")
        order_id = params["order_id"]
        reason = params.get("reason", "customer")
        if reason not in _VALID_REASONS:
            reason = "other"
        refund = params.get("refund", True)

        url = f"{store_url}/admin/api/{_SHOPIFY_API_VERSION}/orders/{order_id}/cancel.json"
        headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
        body = {"reason": reason, "refund": refund}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()

        order = response.json().get("order", {})
        return {
            "cancelled": True,
            "id": order.get("id"),
            "name": order.get("name"),
            "cancelled_at": order.get("cancelled_at"),
            "financial_status": order.get("financial_status"),
            "reason": reason,
        }
