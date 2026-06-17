import asyncio

from app.modules.tools.actions.base_action import BaseAction
from app.modules.tools.actions.google_calendar.calendar_base import (
    build_calendar_service,
    check_advance_notice,
    resolve_calendar_id,
)


class GoogleCalendarUpdateEventAction(BaseAction):
    """
    Updates an existing Google Calendar event (title, start/end time, description).

    Business rule: only events that start more than 1 hour from now can be modified.
    Configurable via config['advance_notice_hours'] (default 1).

    Only the fields you send are updated — omit any field to keep it unchanged.
    """

    ACTION_TYPE = "google_calendar_update_event"
    DEFAULT_DESCRIPTION = (
        "Modifica un evento existente en Google Calendar (título, fecha, hora, descripción). "
        "Solo se pueden modificar eventos con al menos 1 hora de anticipación. "
        "Necesitas el event_id — si el usuario no lo recuerda, consulta primero "
        "la lista de eventos con google_calendar_list_events."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "ID único del evento a modificar."
            },
            "calendar_name": {
                "type": "string",
                "description": "Nombre del calendario/sede donde está el evento."
            },
            "new_title": {
                "type": "string",
                "description": "Nuevo título del evento (opcional)."
            },
            "new_start": {
                "type": "string",
                "description": "Nueva fecha/hora de inicio en ISO 8601 (opcional)."
            },
            "new_end": {
                "type": "string",
                "description": "Nueva fecha/hora de fin en ISO 8601 (opcional)."
            },
            "new_description": {
                "type": "string",
                "description": "Nueva descripción del evento (opcional)."
            }
        },
        "required": ["event_id"]
    }

    async def execute(self, params: dict) -> dict:
        advance_hours = int(self.config.get("advance_notice_hours", 1))
        timezone_str = self.config.get("timezone", "UTC")
        service = build_calendar_service(self.credentials)
        calendar_id, calendar_name = resolve_calendar_id(
            self.config, params.get("calendar_name")
        )
        event_id = params["event_id"]

        # Fetch current event
        event = await asyncio.to_thread(
            lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        )
        current_start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        if current_start:
            check_advance_notice(current_start, hours=advance_hours)

        # Apply only the provided updates
        if params.get("new_title"):
            event["summary"] = params["new_title"]
        if params.get("new_start"):
            event["start"] = {"dateTime": params["new_start"], "timeZone": timezone_str}
        if params.get("new_end"):
            event["end"] = {"dateTime": params["new_end"], "timeZone": timezone_str}
        if params.get("new_description") is not None:
            event["description"] = params["new_description"]

        updated = await asyncio.to_thread(
            lambda: service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event
            ).execute()
        )

        return {
            "updated": True,
            "event_id": updated.get("id"),
            "title": updated.get("summary"),
            "calendar": calendar_name,
            "start": updated.get("start", {}).get("dateTime"),
            "end": updated.get("end", {}).get("dateTime"),
            "html_link": updated.get("htmlLink"),
        }
