from django.db import models


"""

    ERROR_TYPES

"""



class ERROR_TYPES(models.TextChoices):
    ARGS = 'ARGS', 'Invalid or missing arguments provided.'
    PAGINATION = 'PAGINATION', 'Pagination parameters are incorrect or out of range.'
    LOGICAL = 'LOGICAL', 'Logical error due to invalid data or application state.'
    CONSTRAINT = 'CONSTRAINTS', 'Database or business rule constraint violation.'
    PERMISSION = 'PERMISSION', 'Insufficient permissions to perform this action.'
    MISSING_MODEL = 'MISSING_MODEL', 'Requested model instance not found.'
    MISSING = 'MISSING', 'Required data or resource is missing.'
    RESOURCE_LIMIT = 'RESOURCE_LIMIT', 'Resource usage limit has been exceeded.'
    INTERNAL = 'INTERNAL', 'An unexpected internal server error occurred.'

"""

    RESPONSE_CODES

"""

class RESPONSE_CODES(models.TextChoices):
    REQUEST_SENT = 'REQUEST_SENT', 'Error in arguments'