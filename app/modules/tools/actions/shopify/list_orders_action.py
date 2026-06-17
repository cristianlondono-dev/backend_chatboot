import httpx

from app.modules.tools.actions.base_action import BaseAction

_SHOPIFY_API_VERSION = "2024-01"


class ShopifyListOrdersAction(BaseAction):
    """
    Lists recent orders from Shopify for a customer email or phone.

    Required credentials:
      - access_token: str

    Required config:
      - store_url: str  (e.g. "https://mi-tienda.myshopify.com")
    """

    ACTION_TYPE = "shopify_list_orders"
    DEFAULT_DESCRIPTION = (
        "Lista los pedidos recientes en Shopify. "
        "Úsalo cuando el usuario quiera ver su historial de pedidos o buscar un pedido específico."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "Email del cliente para filtrar sus pedidos (opcional)."
            },
            "status": {
                "type": "string",
                "enum": ["open", "closed", "cancelled", "any"],
                "description": "Estado de los pedidos a listar (default: 'any')."
            },
            "limit": {
                "type": "integer",
                "description": "Número máximo de pedidos a devolver (default: 5, máx: 20).",
                "default": 5
            }
        },
        "required": []
    }

    async def execute(self, params: dict) -> dict:
        store_url = self.config.get("store_url", "").rstrip("/")
        access_token = self.credentials.get("access_token", "")
        limit = min(int(params.get("limit", 5)), 20)
        status = params.get("status", "any")

        query_params: dict = {"limit": limit, "status": status}
        if params.get("customer_email"):
            query_params["email"] = params["customer_email"]

        url = f"{store_url}/admin/api/{_SHOPIFY_API_VERSION}/orders.json"
        headers = {"X-Shopify-Access-Token": access_token}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers, params=query_params)
            response.raise_for_status()

        orders = response.json().get("orders", [])
        return {
            "total": len(orders),
            "orders": [
                {
                    "id": o.get("id"),
                    "name": o.get("name"),
                    "financial_status": o.get("financial_status"),
                    "fulfillment_status": o.get("fulfillment_status"),
                    "total_price": o.get("total_price"),
                    "currency": o.get("currency"),
                    "created_at": o.get("created_at"),
                    "item_count": len(o.get("line_items", [])),
                }
                for o in orders
            ]
        }
