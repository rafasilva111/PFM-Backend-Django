from datetime import timedelta
from django.utils import timezone
from pytz import utc
from datetime import datetime

import logging

logger = logging.getLogger('django')

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

    return datetime.fromisoformat(date_str)


def build_paginated_url(request, page_number):
    """
    Helper function to build a URL with an updated 'page' query parameter.
    """
    path = request.path  # Get the path part of the URL
    query_params = request.GET.copy()  # Get a mutable copy of the current query parameters

    # Update the 'page' parameter in query_params
    query_params['page'] = page_number

    # Construct the new URL with updated query parameters
    return f"{path}?{query_params.urlencode()}"