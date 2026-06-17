import httpx

from app.modules.tools.actions.base_action import BaseAction


class CustomRestAction(BaseAction):
    """
    Generic HTTP action — call any REST endpoint.

    Required config:
      - url: str           (supports {param_name} placeholders, e.g. "/orders/{order_id}")
      - method: str        ("GET" | "POST" | "PUT" | "PATCH" | "DELETE")

    Optional config:
      - headers: dict      (static headers merged with credentials.headers)
      - body_template: dict (static body fields merged with call-time params)
      - timeout: int       (seconds, default 10)

    Optional credentials:
      - headers: dict      (secret headers — Authorization, X-API-Key, etc.)

    parameters_schema is fully customised per ToolAction record (no default schema).
    The entire params dict is available for URL interpolation and request body.
    """

    ACTION_TYPE = "custom_rest"
    DEFAULT_DESCRIPTION = "Llama a un endpoint HTTP externo con los parámetros indicados."
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, params: dict) -> dict:
        url_template: str = self.config.get("url", "")
        method: str = self.config.get("method", "GET").upper()
        static_headers: dict = self.config.get("headers", {})
        secret_headers: dict = (self.credentials or {}).get("headers", {})
        body_template: dict = self.config.get("body_template", {})
        timeout: int = int(self.config.get("timeout", 10))

        # Fill URL placeholders with params, then exclude them from query/body
        import re
        url_param_names = set(re.findall(r"\{(\w+)\}", url_template))
        url = url_template.format(**{k: params.get(k, f"{{{k}}}") for k in url_param_names})

        # Only pass params NOT already interpolated into the URL
        extra_params = {k: v for k, v in params.items() if k not in url_param_names}

        headers = {**static_headers, **secret_headers}
        body = {**body_template, **extra_params}

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method in ("GET", "DELETE"):
                response = await client.request(
                    method, url, headers=headers,
                    params=extra_params if extra_params else None
                )
            else:
                response = await client.request(method, url, headers=headers, json=body)
            response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {"raw_response": response.text, "status_code": response.status_code}
