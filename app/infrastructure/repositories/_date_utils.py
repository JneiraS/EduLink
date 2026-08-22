from datetime import date, datetime


def parse_date(value) -> date:
    """Normalize a SQL date string into a date object for chart labels."""
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()