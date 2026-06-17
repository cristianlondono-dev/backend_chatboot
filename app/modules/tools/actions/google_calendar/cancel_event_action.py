import asyncio

from app.modules.tools.actions.base_action import BaseAction
from app.modules.tools.actions.google_calendar.calendar_base import (
    build_calendar_service,
    check_advance_notice,
    resolve_calendar_id,
)


class GoogleCalendarCancelEventAction(BaseAction):
    """
    Cancels (deletes) a Google Calendar event.

    Business rule: only events that start more than 1 hour from now can be cancelled.
    This threshold is configurable via config['advance_notice_hours'] (default 1).
    """

    ACTION_TYPE = "google_calendar_cancel_event"
    DEFAULT_DESCRIPTION = (
        "Cancela un evento del calendario de Google. "
        "Solo se pueden cancelar eventos con al menos 1 hora de anticipación. "
        "Debes conocer el event_id del evento para cancelarlo — si el usuario no lo sabe, "
        "consulta primero la lista de eventos con google_calendar_list_events."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "ID único del evento a cancelar (obtenido de list_events)."
            },
            "calendar_name": {
                "type": "string",
                "description": "Nombre del calendario/sede donde está el evento."
            }
        },
        "required": ["event_id"]
    }

    async def execute(self, params: dict) -> dict:
        advance_hours = int(self.config.get("advance_notice_hours", 1))
        service = build_calendar_service(self.credentials)
        calendar_id, calendar_name = resolve_calendar_id(
            self.config, params.get("calendar_name")
        )
        event_id = params["event_id"]

        # Fetch event to check start time before deleting
        event = await asyncio.to_thread(
            lambda: service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        )
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        if start:
            check_advance_notice(start, hours=advance_hours)

        await asyncio.to_thread(
            lambda: service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        )

        return {
            "cancelled": True,
            "event_id": event_id,
            "title": event.get("summary"),
            "calendar": calendar_name,
            "start": start,
        }
