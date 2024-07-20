from datetime import timedelta, datetime
from django.utils import timezone

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
        date_str (str): The date string in 'DD/MM/YYYYThh:mm:ss' format.

    Returns:
        datetime: A timezone-aware datetime object.

    Raises:
        ValueError: If the date string is in an invalid format.
    """
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%YT%H:%M:%S")
        return timezone.make_aware(date_obj)
    except ValueError:
        raise ValueError("Invalid date format. Please use 'DD/MM/YYYYThh:mm:ss' format.")
