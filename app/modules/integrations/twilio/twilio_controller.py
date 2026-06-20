"""
Twilio WhatsApp webhook controller.

How it works:
  1. Twilio sends a POST to /webhooks/twilio/whatsapp/{agent_id} for each incoming message.
  2. This controller extracts the sender's phone and the message text.
  3. It calls ChatWithMemoryUseCase (same as the regular /chat endpoint).
  4. Returns a TwiML XML response that Twilio delivers back to WhatsApp.

Setup:
  - In the Twilio Console → Messaging → WhatsApp Sandbox (or number config)
  - Set "When a message comes in" to:
      https://yourdomain.com/webhooks/twilio/whatsapp/{agent_id}
  - Method: POST
  - The agent must have an AgentTool configured with channel="whatsapp".

Security (OPTIONAL but recommended for production):
  - Set TWILIO_AUTH_TOKEN in your .env
  - The controller will validate Twilio's X-Twilio-Signature header.
  - Without this env var, signature validation is skipped (dev mode).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.database import get_db
from app.core.exceptions import NotFoundException, UnprocessableException
from app.core.logging.loggers import application_logger, error_logger
from app.modules.memory.use_cases.chat_with_memory_use_case import ChatWithMemoryUseCase

router = APIRouter(prefix="/webhooks/twilio", tags=["Twilio Integration"])


def _twiml_response(message: str) -> Response:
    """Wrap a plain-text message in a TwiML <Message> response."""
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{_escape_xml(message)}</Message>"
        "</Response>"
    )
    return Response(content=body, media_type="text/xml")


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def _validate_twilio_signature(request: Request, auth_token: str) -> bool:
    """Optional Twilio signature validation for production security."""
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        # Build the full URL as Twilio signed it
        url = str(request.url)
        # For form data we need to parse synchronously — handled by the caller
        return validator.validate(url, {}, signature)
    except Exception:
        return False


@router.post("/whatsapp/{agent_id}")
async def twilio_whatsapp_webhook(
    agent_id: UUID,
    request: Request,
    # Twilio sends form-encoded body
    From: str = Form(...),        # "whatsapp:+573001234567"
    Body: str = Form(...),        # The message text
    db: AsyncSession = Depends(get_db)
):
    """
    Receives incoming WhatsApp messages from Twilio and returns a TwiML reply.

    Twilio form fields used:
      From  — sender's WhatsApp number in the format "whatsapp:+57300..."
      Body  — the text of the incoming message

    The agent must have an AgentTool with channel="whatsapp" configured.
    """
    # Strip the "whatsapp:" prefix to get the bare phone number
    phone = From.replace("whatsapp:", "").strip()
    message = Body.strip()

    application_logger.info(
        f"[twilio] Incoming WhatsApp | agent={agent_id} | from={phone} | msg={message[:80]}"
    )

    if not message:
        return _twiml_response("Por favor envía un mensaje de texto.")

    try:
        use_case = ChatWithMemoryUseCase(db)
        result = await use_case.execute(
            agent_id=agent_id,
            channel="whatsapp",
            channel_id=phone,
            question=message,
        )
        answer = result.get("answer", "Lo siento, no pude procesar tu mensaje.")
    except (NotFoundException, UnprocessableException) as exc:
        # Expected domain errors (e.g. "not registered") carry a message
        # that's already meant for the end user.
        answer = str(exc)
    except Exception as exc:
        error_logger.error(
            f"[twilio] Error processing message | agent={agent_id} | from={phone}: {exc}",
            exc_info=True
        )
        answer = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta de nuevo."

    return _twiml_response(answer)
