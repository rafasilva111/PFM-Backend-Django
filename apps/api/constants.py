from django.db import models


"""

    ERROR_TYPES

"""



class ERROR_TYPES(models.TextChoices):
    ARGS = 'ARGS', 'Error in arguments'
    PAGINATION = 'PAGINATION', 'Error in pagination'
    LOGICAL = 'LOGICAL', 'Error in using faulty data to app logic'
    CONSTRAINT = 'CONSTRAINTS', 'Error in a constraint'
    MISSING_MODEL = 'MISSING_MODEL', 'Error find model'
    MISSING = 'MISSING', 'Error model missing something.'


"""

    RESPONSE_CODES

"""

class RESPONSE_CODES(models.TextChoices):
    REQUEST_SENT = 'REQUEST_SENT', 'Error in arguments'