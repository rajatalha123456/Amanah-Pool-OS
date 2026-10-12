"""Working-day calendars of a pool (BRD section 5 "Identity": calendar)."""

from rest_framework.exceptions import ValidationError

CALENDARS = {
    "daily": {0, 1, 2, 3, 4, 5, 6},
    "mon_fri": {0, 1, 2, 3, 4},  # Monday = 0
    "sun_thu": {6, 0, 1, 2, 3},
}
LABELS = {"daily": "Every day", "mon_fri": "Monday to Friday", "sun_thu": "Sunday to Thursday"}


def is_working_day(pool, day):
    return day.weekday() in CALENDARS.get(pool.calendar, CALENDARS["daily"])


def assert_working_day(pool, day, what="This date"):
    if not is_working_day(pool, day):
        raise ValidationError(f"{what} ({day}) is not a working day in the pool's calendar ({LABELS.get(pool.calendar, pool.calendar)}).")
