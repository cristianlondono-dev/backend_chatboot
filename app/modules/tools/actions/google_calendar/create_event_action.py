import asyncio

from app.modules.tools.actions.base_action import BaseAction
from app.modules.tools.actions.google_calendar.calendar_base import (
    build_calendar_service,
    resolve_calendar_id,
)


class GoogleCalendarCreateEventAction(BaseAction):
    """
    Creates an event in a Google Calendar.

    Supports multiple calendars — the LLM picks by name using calendar_name.

    Config (multi-calendar):
      {
        "calendars": [
          {"id": "sede1@group.calendar.google.com", "name": "Sede Centro"},
          {"id": "sede2@group.calendar.google.com", "name": "Sede Norte"},
          {"id": "sede3@group.calendar.google.com", "name": "Sede Sur"}
        ],
        "timezone": "America/Bogota"
      }

    Config (single calendar / simple):
      { "calendar_id": "primary", "timezone": "America/Bogota" }
    """

    ACTION_TYPE = "google_calendar_create_event"
    DEFAULT_DESCRIPTION = (
        "Crea un evento en Google Calendar. "
        "Úsalo cuando el usuario quiera agendar una reunión, cita o recordatorio. "
        "Si hay varios calendarios disponibles, pregunta en cuál agendar."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "calendar_name": {
                "type": "string",
                "description": (
                    "Nombre del calendario/sede donde crear el evento. "
                    "Omitir si solo hay un calendario configurado."
                )
            },
            "title": {
                "type": "string",
                "description": "Título del evento."
            },
            "start": {
                "type": "string",
                "description": "Fecha y hora de inicio en ISO 8601 (e.g. '2025-07-15T10:00:00')."
            },
            "end": {
                "type": "string",
                "description": "Fecha y hora de fin en ISO 8601 (e.g. '2025-07-15T11:00:00')."
            },
            "description": {
                "type": "string",
                "description": "Descripción o notas adicionales (opcional)."
            },
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de correos de los asistentes (opcional)."
            }
        },
        "required": ["title", "start", "end"]
    }

    async def execute(self, params: dict) -> dict:
        timezone_str = self.config.get("timezone", "UTC")
        calendar_id, calendar_name = resolve_calendar_id(
            self.config, params.get("calendar_name")
        )

        event_body = {
            "summary": params["title"],
            "start": {"dateTime": params["start"], "timeZone": timezone_str},
            "end": {"dateTime": params["end"], "timeZone": timezone_str},
        }
        if params.get("description"):
            event_body["description"] = params["description"]
        if params.get("attendees"):
            event_body["attendees"] = [{"email": e} for e in params["attendees"]]

        service = build_calendar_service(self.credentials)

        event = await asyncio.to_thread(
            lambda: service.events().insert(calendarId=calendar_id, body=event_body).execute()
        )

        return {
            "event_id": event.get("id"),
            "title": event.get("summary"),
            "calendar": calendar_name,
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "html_link": event.get("htmlLink"),
            "status": event.get("status"),
        }
