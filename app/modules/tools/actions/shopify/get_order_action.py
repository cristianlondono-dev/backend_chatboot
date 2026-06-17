import httpx

from app.modules.tools.actions.base_action import BaseAction

_SHOPIFY_API_VERSION = "2024-01"


class ShopifyGetOrderAction(BaseAction):
    """
    Retrieves order details from Shopify.

    Required credentials:
      - access_token: str  (Shopify Admin API access token)

    Required config:
      - store_url: str  (e.g. "https://mi-tienda.myshopify.com")
    """

    ACTION_TYPE = "shopify_get_order"
    DEFAULT_DESCRIPTION = (
        "Consulta el estado y los detalles de un pedido en Shopify. "
        "Úsalo cuando el usuario pregunte por el estado, items o envío de un pedido."
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

        url = f"{store_url}/admin/api/{_SHOPIFY_API_VERSION}/orders/{order_id}.json"
        headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        order = response.json().get("order", {})
        return {
            "id": order.get("id"),
            "name": order.get("name"),
            "financial_status": order.get("financial_status"),
            "fulfillment_status": order.get("fulfillment_status"),
            "total_price": order.get("total_price"),
            "currency": order.get("currency"),
            "email": order.get("email"),
            "line_items": [
                {
                    "title": item.get("title"),
                    "quantity": item.get("quantity"),
                    "price": item.get("price"),
                }
                for item in order.get("line_items", [])
            ],
            "tracking_numbers": [
                number
                for fulfillment in order.get("fulfillments", [])
                for number in fulfillment.get("tracking_numbers", [])
            ],
        }
