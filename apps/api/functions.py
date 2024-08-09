from datetime import timedelta
from django.utils import timezone
from pytz import utc
def add_days(date_obj, days):
    """
    Add a specified number of days to a given datetime object, considering timezone.

    Args:
        date_obj (datetime): The original datetime object.
        days (int): The number of days to add.

    Returns:
        datetime: A new datetime object with the added days.
    """
    if timezone.is_naive(date_obj):
        date_obj = timezone.make_aware(date_obj)
    new_date = date_obj + timedelta(days=days)
    return new_date

def parse_date(date_str):
    """
    Parse a date string to a timezone-aware datetime object.

    Args:
        date_str (str): The date string in '2024-07-17T13:37:40.087Z' or '2024-07-17T13:37:40Z' format.

    Returns:
        datetime: A timezone-aware datetime object.

    Raises:
        ValueError: If the date string is in an invalid format.
    """
    try:
        # Try parsing the date string with fractional seconds
        aware_datetime = timezone.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=utc)
    except ValueError:
        try:
            # Try parsing the date string without fractional seconds
            aware_datetime = timezone.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=utc)
        except ValueError:
            print(f"Error parsing date string '{date_str}'")
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DDTHH:MM:SS.sssZ' or 'YYYY-MM-DDTHH:MM:SSZ' format.")
    return aware_datetime