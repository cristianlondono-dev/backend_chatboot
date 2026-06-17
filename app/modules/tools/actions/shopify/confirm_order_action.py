import httpx

from app.modules.tools.actions.base_action import BaseAction

_SHOPIFY_API_VERSION = "2024-01"


class ShopifyConfirmOrderAction(BaseAction):
    """
    Confirms (closes) an open order in Shopify.

    Required credentials:
      - access_token: str  (Shopify Admin API access token)

    Required config:
      - store_url: str  (e.g. "https://mi-tienda.myshopify.com")
    """

    ACTION_TYPE = "shopify_confirm_order"
    DEFAULT_DESCRIPTION = (
        "Confirma un pedido en Shopify marcándolo como cerrado. "
        "Úsalo cuando el usuario quiera confirmar o cerrar un pedido."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "ID numérico del pedido en Shopify (sin el símbolo #)."
            }
        },
        "required": ["order_id"]
    }

    async def execute(self, params: dict) -> dict:
        store_url = self.config.get("store_url", "").rstrip("/")
        access_token = self.credentials.get("access_token", "")
        order_id = params["order_id"]

        url = f"{store_url}/admin/api/{_SHOPIFY_API_VERSION}/orders/{order_id}/close.json"
        headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()

        order = response.json().get("order", {})
        return {
            "id": order.get("id"),
            "name": order.get("name"),
            "closed_at": order.get("closed_at"),
            "status": "closed",
        }
