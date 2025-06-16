
from os import environ
from django.conf import settings

## Websocket
WEBSOCKET_URL = environ.get('WEBSOCKET_URL')


## Firebase Storage


FIREBASE_STORAGE_BASE_BUCKET = "images"

FIREBASE_STORAGE_COMPANY_BUCKET = f"{FIREBASE_STORAGE_BASE_BUCKET}/company/"


"""

    Management Accounts

"""

AUTOMATION_ACCOUNT = 'Automation'

AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD = environ.get('AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD','password')

"""

    Company Accounts

"""

COMPANY_PINGO_DOCE = 'Pingo Doce'

COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD = environ.get('COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD','password')

COMPANY_CONTINENTE = 'Continente'

COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD = environ.get('COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD','password')

COMPANY_IMAGES_ROOT_PATH = "src/assets/img/company/"


"""

    Premium Accounts Privileges

"""

##
#   User App

MAX_USER_NORMAL_SAVED_RECIPES = 25

MAX_USER_PREMIUM_SAVED_RECIPES = 100

##
#   Shopping List App

# Shopping Lists

MAX_USER_NORMAL_SHOPPING_LISTS = 5

MAX_USER_PREMIUM_SHOPPING_LISTS = 15

MAX_USER_NORMAL_SHOPPING_LISTS_GROUPS = 5

MAX_USER_PREMIUM_SHOPPING_LISTS_GROUPS = 10

# Groups

MAX_USER_NORMAL_GROUPS = 5

MAX_USER_PREMIUM_GROUPS = 20

"""

    Testing Accounts

"""

TESTING_ACCOUNT_A = 'a'

TESTING_ACCOUNT_A_PASSWORD = environ.get('TESTING_ACCOUNT_A','a')

TESTING_ACCOUNT_B = 'b'

TESTING_ACCOUNT_B_PASSWORD = environ.get('TESTING_ACCOUNT_B','b')

TESTING_ACCOUNT_C = 'c'

TESTING_ACCOUNT_C_PASSWORD = environ.get('TESTING_ACCOUNT_C','c')


"""

    Email Constants

"""

INVITATION_EMAIL_SUBJECT = 'You were invited to join the GoodBites Backend!'