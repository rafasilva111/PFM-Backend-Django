###
#       General imports
##

from apps.common.tests.constants import TESTING_ACCOUNT_A, TESTING_ACCOUNT_A_PASSWORD, TESTING_ACCOUNT_B, TESTING_ACCOUNT_B_PASSWORD, TESTING_ACCOUNT_C, TESTING_ACCOUNT_C_PASSWORD
from apps.user_app.models import User,Company
from django.test import TestCase

##
#   Extras
#

import inspect



def print_prologue():
    
    print("----------------------------------------------------------------------")
    print("\n")
    print(f"Running test: {inspect.currentframe().f_back.f_code.co_name}")
    print("\n")



def create_test_users(self: TestCase):
    # Create predefined users A, B, C
        
    self.user_a = User.objects.create(
            name=TESTING_ACCOUNT_A,
            email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt",
            is_staff=True,
            is_superuser=True,
        )
    self.user_a.set_password(TESTING_ACCOUNT_A_PASSWORD)
    self.user_a.save()
    
    self.user_b = User.objects.create(
            name=TESTING_ACCOUNT_B,
            email=f"{TESTING_ACCOUNT_B}@{TESTING_ACCOUNT_B}.pt",
            is_staff=True,
            is_superuser=False,
        )
    self.user_b.set_password(TESTING_ACCOUNT_B_PASSWORD)
    self.user_b.save()
    
    self.user_c = User.objects.create(
            name=TESTING_ACCOUNT_C,
            email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt",
            is_staff=False,
            is_superuser=False,
        )
    self.user_c.set_password(TESTING_ACCOUNT_C_PASSWORD)
    self.user_c.save()
    
def create_test_company(self: TestCase):
    # Create a company for testing
    
    self.company = Company.objects.create(
        name='Goodbites'
    )
    
    
    