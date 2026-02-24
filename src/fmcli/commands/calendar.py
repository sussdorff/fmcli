from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import caldav
from icalendar import Calendar as iCal, Event as iEvent

from fmcli.account import Account


def _get_client(account: Account, client: Any = None) -> caldav.DAVClient:
    return client if client is not None else account.get_caldav_client()


def _get_default_calendar(dav_client: caldav.DAVClient) -> caldav.Calendar:
    return dav_client.principal().calendars()[0]


def list_events(account: Account, days: int = 30, client: Any = None) -> list[dict]:
    """Return events from the default calendar within the next ``days`` days.

    Each event is represented as a dict with keys: id, title, start, end, location.
    """
    c = _get_client(account, client)
    cal = _get_default_calendar(c)
    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(days=days)
    events = cal.search(start=now, end=end, event=True)
    result = []
    for ev in events:
        vevent = ev.vobject_instance.vevent
        end_val = str(vevent.dtend.value) if hasattr(vevent, "dtend") else ""
        result.append({
            "id": str(vevent.uid.value),
            "title": str(vevent.summary.value),
            "start": str(vevent.dtstart.value),
            "end": end_val,
            "location": str(vevent.location.value) if hasattr(vevent, "location") else "",
        })
    return result


def create_event(
    account: Account,
    title: str,
    start: str,
    end: str,
    location: str = "",
    client: Any = None,
) -> str:
    """Create a new event in the default calendar.

    Args:
        account: The Fastmail account to use.
        title: Event summary/title.
        start: ISO 8601 start datetime string, e.g. "2024-01-15T10:00:00".
        end: ISO 8601 end datetime string, e.g. "2024-01-15T11:00:00".
        location: Optional location string.
        client: Optional pre-constructed caldav.DAVClient (for testing).

    Returns:
        The UID string of the newly created event.
    """
    c = _get_client(account, client)
    cal = _get_default_calendar(c)

    uid = str(uuid.uuid4())
    ical = iCal()
    event = iEvent()
    event.add("summary", title)
    event.add("dtstart", datetime.fromisoformat(start))
    event.add("dtend", datetime.fromisoformat(end))
    event.add("uid", uid)
    if location:
        event.add("location", location)
    ical.add_component(event)
    cal.add_event(ical.to_ical())
    return uid


def update_event(
    account: Account,
    uid: str,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    client: Any = None,
) -> None:
    """Update fields on an existing event identified by UID.

    Args:
        account: The Fastmail account to use.
        uid: The UID of the event to update.
        title: New summary/title, or None to leave unchanged.
        start: New ISO 8601 start datetime string, or None to leave unchanged.
        end: New ISO 8601 end datetime string, or None to leave unchanged.
        client: Optional pre-constructed caldav.DAVClient (for testing).
    """
    c = _get_client(account, client)
    cal = _get_default_calendar(c)
    event = cal.event_by_uid(uid)
    vevent = event.vobject_instance.vevent

    if title is not None:
        vevent.summary.value = title
    if start is not None:
        vevent.dtstart.value = datetime.fromisoformat(start)
    if end is not None:
        vevent.dtend.value = datetime.fromisoformat(end)

    event.save()


def delete_event(account: Account, uid: str, client: Any = None) -> None:
    """Delete an event by UID from the default calendar.

    Args:
        account: The Fastmail account to use.
        uid: The UID of the event to delete.
        client: Optional pre-constructed caldav.DAVClient (for testing).

    Raises:
        ValueError: If no event with the given UID is found.
    """
    c = _get_client(account, client)
    cal = _get_default_calendar(c)
    try:
        event = cal.event_by_uid(uid)
    except Exception as exc:
        raise ValueError(f"Event with uid '{uid}' not found") from exc
    event.delete()
