from __future__ import annotations

import datetime
import pytest

from fmcli.account import Account
from fmcli.config import AccountConfig
from fmcli.commands import calendar as cal_cmd


@pytest.fixture
def account() -> Account:
    return Account(
        name="personal",
        email="user@fastmail.com",
        token="tok123",
        app_password="apppass",
    )


def _make_mock_event(mocker, uid: str, summary: str, dtstart, dtend, location=None):
    """Build a mock caldav.Event with vobject_instance populated."""
    mock_ev = mocker.MagicMock()
    vevent = mocker.MagicMock()
    vevent.uid.value = uid
    vevent.summary.value = summary
    vevent.dtstart.value = dtstart
    vevent.dtend.value = dtend
    if location is not None:
        vevent.location.value = location
        type(vevent).location = mocker.PropertyMock(return_value=vevent.location)
    else:
        # hasattr returns False for non-existent attributes on MagicMock by default,
        # but we need to explicitly make location absent
        del vevent.location
    mock_ev.vobject_instance.vevent = vevent
    # icalendar_component for update path
    mock_ev.icalendar_component = mocker.MagicMock()
    mock_ev.icalendar_component.get.side_effect = lambda key, default=None: {
        "uid": uid,
        "summary": summary,
    }.get(key.lower(), default)
    return mock_ev


def _setup_mock_client(mocker, events: list):
    """Return (mock_client, mock_calendar) with events set up."""
    mock_client = mocker.MagicMock()
    mock_principal = mocker.MagicMock()
    mock_calendar = mocker.MagicMock()
    mock_client.principal.return_value = mock_principal
    mock_principal.calendars.return_value = [mock_calendar]
    mock_calendar.search.return_value = events
    return mock_client, mock_calendar


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------

def test_list_events(mocker, account):
    now = datetime.datetime(2024, 1, 15, 10, 0)
    end = datetime.datetime(2024, 1, 15, 11, 0)
    ev1 = _make_mock_event(mocker, "uid-1", "Meeting", now, end, location="Room A")
    ev2 = _make_mock_event(mocker, "uid-2", "Lunch", now, end)

    mock_client, _ = _setup_mock_client(mocker, [ev1, ev2])

    result = cal_cmd.list_events(account, days=30, client=mock_client)

    assert len(result) == 2
    assert result[0]["id"] == "uid-1"
    assert result[0]["title"] == "Meeting"
    assert result[0]["location"] == "Room A"
    assert result[1]["id"] == "uid-2"
    assert result[1]["title"] == "Lunch"
    assert result[1]["location"] == ""


def test_list_events_empty(mocker, account):
    mock_client, _ = _setup_mock_client(mocker, [])

    result = cal_cmd.list_events(account, days=7, client=mock_client)

    assert result == []


def test_list_events_returns_start_end_as_strings(mocker, account):
    start_dt = datetime.datetime(2024, 3, 1, 9, 0)
    end_dt = datetime.datetime(2024, 3, 1, 10, 0)
    ev = _make_mock_event(mocker, "uid-x", "Standup", start_dt, end_dt)
    mock_client, _ = _setup_mock_client(mocker, [ev])

    result = cal_cmd.list_events(account, client=mock_client)

    assert result[0]["start"] == str(start_dt)
    assert result[0]["end"] == str(end_dt)


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------

def test_create_event(mocker, account):
    mock_client, mock_calendar = _setup_mock_client(mocker, [])

    uid = cal_cmd.create_event(
        account,
        title="Team Sync",
        start="2024-06-01T14:00:00",
        end="2024-06-01T15:00:00",
        client=mock_client,
    )

    # Verify a UID string was returned
    assert isinstance(uid, str)
    assert len(uid) == 36  # UUID4 format

    # Verify calendar.add_event was called with ical bytes
    mock_calendar.add_event.assert_called_once()
    ical_bytes = mock_calendar.add_event.call_args[0][0]
    assert b"Team Sync" in ical_bytes
    assert uid.encode() in ical_bytes


def test_create_event_with_location(mocker, account):
    mock_client, mock_calendar = _setup_mock_client(mocker, [])

    cal_cmd.create_event(
        account,
        title="Offsite",
        start="2024-07-10T09:00:00",
        end="2024-07-10T17:00:00",
        location="Berlin HQ",
        client=mock_client,
    )

    ical_bytes = mock_calendar.add_event.call_args[0][0]
    assert b"Berlin HQ" in ical_bytes


def test_create_event_without_location_omits_location_field(mocker, account):
    mock_client, mock_calendar = _setup_mock_client(mocker, [])

    cal_cmd.create_event(
        account,
        title="Solo Work",
        start="2024-07-10T09:00:00",
        end="2024-07-10T17:00:00",
        client=mock_client,
    )

    ical_bytes = mock_calendar.add_event.call_args[0][0]
    assert b"LOCATION" not in ical_bytes


# ---------------------------------------------------------------------------
# update_event
# ---------------------------------------------------------------------------

def _make_event_with_uid(mocker, uid: str):
    """Return a mock event that calendar.event_by_uid(uid) would return."""
    mock_ev = mocker.MagicMock()
    vevent = mocker.MagicMock()
    vevent.uid.value = uid
    vevent.summary.value = "Old Title"
    vevent.dtstart.value = datetime.datetime(2024, 1, 1, 10, 0)
    vevent.dtend.value = datetime.datetime(2024, 1, 1, 11, 0)
    mock_ev.vobject_instance.vevent = vevent
    return mock_ev


def _setup_client_with_event_by_uid(mocker, uid: str):
    mock_client = mocker.MagicMock()
    mock_principal = mocker.MagicMock()
    mock_calendar = mocker.MagicMock()
    mock_client.principal.return_value = mock_principal
    mock_principal.calendars.return_value = [mock_calendar]
    mock_ev = _make_event_with_uid(mocker, uid)
    mock_calendar.event_by_uid.return_value = mock_ev
    return mock_client, mock_calendar, mock_ev


def test_update_event_title(mocker, account):
    mock_client, mock_calendar, mock_ev = _setup_client_with_event_by_uid(
        mocker, "uid-abc"
    )

    cal_cmd.update_event(account, uid="uid-abc", title="New Title", client=mock_client)

    mock_calendar.event_by_uid.assert_called_once_with("uid-abc")
    assert mock_ev.vobject_instance.vevent.summary.value == "New Title"
    mock_ev.save.assert_called_once()


def test_update_event_start(mocker, account):
    mock_client, mock_calendar, mock_ev = _setup_client_with_event_by_uid(
        mocker, "uid-start"
    )
    new_start = datetime.datetime(2024, 5, 5, 8, 0)

    cal_cmd.update_event(
        account, uid="uid-start", start="2024-05-05T08:00:00", client=mock_client
    )

    assert mock_ev.vobject_instance.vevent.dtstart.value == new_start
    mock_ev.save.assert_called_once()


def test_update_event_end(mocker, account):
    mock_client, mock_calendar, mock_ev = _setup_client_with_event_by_uid(
        mocker, "uid-end"
    )
    new_end = datetime.datetime(2024, 5, 5, 18, 0)

    cal_cmd.update_event(
        account, uid="uid-end", end="2024-05-05T18:00:00", client=mock_client
    )

    assert mock_ev.vobject_instance.vevent.dtend.value == new_end
    mock_ev.save.assert_called_once()


def test_update_event_no_changes_still_saves(mocker, account):
    mock_client, mock_calendar, mock_ev = _setup_client_with_event_by_uid(
        mocker, "uid-noop"
    )

    cal_cmd.update_event(account, uid="uid-noop", client=mock_client)

    mock_ev.save.assert_called_once()


# ---------------------------------------------------------------------------
# delete_event
# ---------------------------------------------------------------------------

def test_delete_event(mocker, account):
    mock_client = mocker.MagicMock()
    mock_principal = mocker.MagicMock()
    mock_calendar = mocker.MagicMock()
    mock_client.principal.return_value = mock_principal
    mock_principal.calendars.return_value = [mock_calendar]
    mock_ev = mocker.MagicMock()
    mock_calendar.event_by_uid.return_value = mock_ev

    cal_cmd.delete_event(account, uid="uid-del", client=mock_client)

    mock_calendar.event_by_uid.assert_called_once_with("uid-del")
    mock_ev.delete.assert_called_once()


def test_delete_event_not_found(mocker, account):
    mock_client = mocker.MagicMock()
    mock_principal = mocker.MagicMock()
    mock_calendar = mocker.MagicMock()
    mock_client.principal.return_value = mock_principal
    mock_principal.calendars.return_value = [mock_calendar]
    mock_calendar.event_by_uid.side_effect = Exception("404 Not Found")

    with pytest.raises(ValueError, match="uid-missing"):
        cal_cmd.delete_event(account, uid="uid-missing", client=mock_client)
