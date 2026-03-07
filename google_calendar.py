from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials

def get_service():
    return build("calendar", "v3", credentials=get_credentials())

def get_events(period="today"):
    now = datetime.now(timezone.utc)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif period == "month":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=30)
    else:
        start = now
        end = now + timedelta(days=1)

    service = get_service()
    results = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = results.get("items", [])
    if not events:
        return f"No events for {period}."

    lines = [f"Calendar ({period}):"]
    for e in events:
        start_str = e["start"].get("dateTime", e["start"].get("date"))
        try:
            dt = datetime.fromisoformat(start_str).strftime("%a %b %d %H:%M")
        except Exception:
            dt = start_str
        lines.append(f"  {dt} - {e.get('summary', '(no title)')} [id:{e['id']}]")

    return "\n".join(lines)

def create_event(title, start_datetime, end_datetime, description=None):
    service = get_service()
    event = {
        "summary": title,
        "start": {"dateTime": start_datetime, "timeZone": "UTC"},
        "end":   {"dateTime": end_datetime,   "timeZone": "UTC"},
    }
    if description:
        event["description"] = description

    created = service.events().insert(calendarId="primary", body=event).execute()
    return f"Event created: {created.get('summary')} [id:{created.get('id')}]"

def delete_event(event_id):
    service = get_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Event {event_id} deleted."

def update_event(event_id, title=None, start_datetime=None, end_datetime=None, description=None):
    service = get_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    if title:
        event["summary"] = title
    if start_datetime:
        event["start"] = {"dateTime": start_datetime, "timeZone": "UTC"}
    if end_datetime:
        event["end"] = {"dateTime": end_datetime, "timeZone": "UTC"}
    if description:
        event["description"] = description

    updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
    return f"Event updated: {updated.get('summary')} [id:{updated.get('id')}]"
