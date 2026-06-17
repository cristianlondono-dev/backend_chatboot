import asyncio
from datetime import datetime, timezone

from app.modules.tools.actions.base_action import BaseAction
from app.modules.tools.actions.google_calendar.calendar_base import (
    build_calendar_service,
    resolve_calendar_id,
)


class GoogleCalendarListEventsAction(BaseAction):
    """
    Lists upcoming events from one or all configured Google Calendars.

    When calendar_name is omitted, queries ALL configured calendars and
    merges results sorted by start time.
    """

    ACTION_TYPE = "google_calendar_list_events"
    DEFAULT_DESCRIPTION = (
        "Lista los próximos eventos del calendario de Google. "
        "Puede consultar un calendario específico o todos a la vez. "
        "Úsalo cuando el usuario quiera saber qué reuniones o citas tiene agendadas."
    )
    DEFAULT_PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "calendar_name": {
                "type": "string",
                "description": (
                    "Nombre del calendario/sede a consultar. "
                    "Si se omite, consulta todos los calendarios disponibles."
                )
            },
            "time_min": {
                "type": "string",
                "description": (
                    "Fecha/hora mínima en ISO 8601 (inclusive). "
                    "Por defecto: el momento actual."
                )
            },
            "time_max": {
                "type": "string",
                "description": "Fecha/hora máxima en ISO 8601 (exclusiva)."
            },
            "max_results": {
                "type": "integer",
                "description": "Número máximo de eventos a devolver (default 10).",
                "default": 10
            }
        },
        "required": []
    }

    async def execute(self, params: dict) -> dict:
        service = build_calendar_service(self.credentials)
        time_min = params.get("time_min") or datetime.now(timezone.utc).isoformat()
        time_max = params.get("time_max")
        max_results = int(params.get("max_results", 10))

        calendars: list[dict] = self.config.get("calendars", [])
        calendar_name_param = params.get("calendar_name")

        # Decide which calendars to query
        if calendar_name_param:
            cal_id, cal_name = resolve_calendar_id(self.config, calendar_name_param)
            targets = [{"id": cal_id, "name": cal_name}]
        elif calendars:
            targets = calendars
        else:
            fallback_id = self.config.get("calendar_id", "primary")
            targets = [{"id": fallback_id, "name": fallback_id}]

        async def fetch_calendar(cal: dict) -> list[dict]:
            kwargs = {
                "calendarId": cal["id"],
                "timeMin": time_min,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_max:
                kwargs["timeMax"] = time_max

            result = await asyncio.to_thread(
                lambda: service.events().list(**kwargs).execute()
            )
            return [
                {
                    "event_id": e.get("id"),
                    "title": e.get("summary"),
                    "calendar": cal["name"],
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "description": e.get("description"),
                    "html_link": e.get("htmlLink"),
                    "status": e.get("status"),
                }
                for e in result.get("items", [])
            ]

        # Fetch all targets concurrently
        import asyncio as _asyncio
        results_per_cal = await _asyncio.gather(*[fetch_calendar(c) for c in targets])
        all_events = [evt for cal_events in results_per_cal for evt in cal_events]

        # Sort merged results by start time
        all_events.sort(key=lambda e: e.get("start") or "")

        return {
            "total": len(all_events),
            "calendars_queried": [c["name"] for c in targets],
            "events": all_events[:max_results],
        }
