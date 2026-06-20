import httpx

from app.core.logging.loggers import application_logger, error_logger
from app.modules.tools.actions.base_action import BaseAction


class HumanHandoffAction(BaseAction):
    """
    Escala la conversación a un humano. No resuelve el caso por sí misma —
    el registro real del escalamiento (fuente de verdad) lo crea el caller
    (ChatWithMemoryUseCase) en la tabla `escalations`, porque esta acción no
    tiene acceso a la sesión de base de datos. El webhook aquí es solo una
    notificación best-effort opcional.

    Optional config:
      - webhook_url: str | None   (si se configura, se hace POST de notificación)
      - method: str                (default "POST")
      - timeout: int               (segundos, default 10)

    Optional credentials:
      - headers: dict               (ej. Authorization para el webhook)
    """

    ACTION_TYPE = "human_handoff"
    DEFAULT_DESCRIPTION = (
        "Escala la conversación a un humano. Úsala SIEMPRE que el usuario pida un documento "
        "formal (carta laboral, certificado, contrato, cotización) o cualquier otra solicitud "
        "que requiera intervención humana y no pueda resolverse en el chat."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "resumen": {
                "type": "string",
                "description": (
                    "Resumen breve de lo que el usuario necesita, para que el humano que "
                    "atienda tenga contexto."
                )
            }
        },
        "required": ["resumen"]
    }

    async def execute(self, params: dict) -> dict:
        webhook_url = (self.config or {}).get("webhook_url")
        resumen = params.get("resumen", "")

        if webhook_url:
            method = (self.config or {}).get("method", "POST").upper()
            timeout = int((self.config or {}).get("timeout", 10))
            headers = (self.credentials or {}).get("headers", {})
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(
                        method, webhook_url, headers=headers, json={"resumen": resumen}
                    )
                    response.raise_for_status()
                application_logger.info(f"[human-handoff] Webhook notificado: {webhook_url}")
            except Exception as exc:
                # Best-effort: el webhook es solo notificación, no la fuente de verdad
                # (el registro en la tabla `escalations` no depende de esto).
                error_logger.error(
                    f"[human-handoff] Webhook falló (no bloqueante): {exc}", exc_info=True
                )

        return {
            "escalado": True,
            "mensaje": "Tu solicitud fue escalada a un humano, te contactaremos pronto."
        }
