"""
Shared utilities for all Google Calendar actions.

Multi-calendar config format:
  config = {
    "calendars": [
      {"id": "sede1@group.calendar.google.com", "name": "Sede Centro"},
      {"id": "sede2@group.calendar.google.com", "name": "Sede Norte"}
    ],
    "timezone": "America/Bogota",
    # Fallback for single-calendar setup (legacy / simple use case):
    "calendar_id": "primary"
  }

Credential modes:
  Option A — Service Account (server-to-server, recommended):
    credentials = { "service_account_json": { ...full JSON... } }

  Option B — OAuth2 user token:
    credentials = { "oauth_token": "ya29.xxxx" }
"""
from datetime import datetime, timezone, timedelta


def build_calendar_service(credentials: dict):
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client is required. "
            "Install with: pip install google-api-python-client google-auth"
        ) from exc

    if "service_account_json" in credentials:
        creds = service_account.Credentials.from_service_account_info(
            credentials["service_account_json"],
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
    elif "oauth_token" in credentials:
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=credentials["oauth_token"])
    else:
        raise ValueError(
            "Google Calendar credentials must contain 'service_account_json' or 'oauth_token'."
        )

    return build("calendar", "v3", credentials=creds)


def resolve_calendar_id(config: dict, calendar_name: str | None) -> tuple[str, str]:
    """
    Resolve a calendar name → (calendar_id, resolved_name).

    If multiple calendars are configured, matches by name (case-insensitive).
    Falls back to 'primary' or config['calendar_id'] if no name given.
    Returns (calendar_id, display_name).
    """
    calendars: list[dict] = config.get("calendars", [])

    if calendar_name and calendars:
        name_lower = calendar_name.lower()
        for cal in calendars:
            if cal.get("name", "").lower() == name_lower:
                return cal["id"], cal["name"]
        # partial match
        for cal in calendars:
            if name_lower in cal.get("name", "").lower():
                return cal["id"], cal["name"]
        raise ValueError(
            f"No se encontró el calendario '{calendar_name}'. "
            f"Disponibles: {', '.join(c['name'] for c in calendars)}"
        )

    # Single-calendar or fallback
    if calendars:
        cal = calendars[0]
        return cal["id"], cal["name"]

    fallback = config.get("calendar_id", "primary")
    return fallback, fallback


def check_advance_notice(event_start_iso: str, hours: int = 1) -> None:
    """
    Raise ValueError if the event starts within `hours` from now.
    event_start_iso should be an ISO 8601 string with or without timezone.
    """
    try:
        # Try with timezone
        start_dt = datetime.fromisoformat(event_start_iso)
    except ValueError:
        return  # can't parse, skip the check

    now = datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        # Treat as UTC if no timezone info
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    deadline = now + timedelta(hours=hours)
    if start_dt <= deadline:
        raise ValueError(
            f"No es posible modificar o cancelar eventos con menos de {hours} hora(s) de anticipación. "
            f"El evento comienza a las {start_dt.strftime('%H:%M')} y son las {now.strftime('%H:%M')} (UTC)."
        )
