from django.core.management.base import BaseCommand
from apps.user_app.models import User,Company
from apps.common.constants import TESTING_ACCOUNT_A, TESTING_ACCOUNT_A_PASSWORD, TESTING_ACCOUNT_B, TESTING_ACCOUNT_B_PASSWORD, TESTING_ACCOUNT_C, TESTING_ACCOUNT_C_PASSWORD
from apps.common.functions import lower_and_underescore
from django.utils import timezone
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):
        
        # Check if the default company exists
        try:
            default_company = Company.objects.get(
                name='Goodbites'
            )
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR('You need to create the default company first'))
            return

        # A
        name_a = lower_and_underescore(TESTING_ACCOUNT_A)
        
        try:
            testing_account_a = User.objects.get(
                email=f'{name_a}@{name_a}.pt'
            )
            
            self.stdout.write(self.style.SUCCESS('Account A already exists'))
        except User.DoesNotExist:
            testing_account_a = User(
                name=name_a,
                email=f'{name_a}@{name_a}.pt',
                is_staff=True,
                is_superuser=True,
                birth_date=timezone.now(),
                company=default_company
            )
            testing_account_a.set_password(TESTING_ACCOUNT_A_PASSWORD)
            testing_account_a.save()
            self.stdout.write(self.style.SUCCESS('Successfully created testing account A'))
        
        # B
        name_b = lower_and_underescore(TESTING_ACCOUNT_B)

        try:
            testing_account_b = User.objects.get(
                email=f'{name_b}@{name_b}.pt'
            )
            
            self.stdout.write(self.style.SUCCESS('Account B already exists'))   
        except User.DoesNotExist:
            testing_account_b = User(
                name=name_b,
                email=f'{name_b}@{name_b}.pt',
                is_staff=True,
                birth_date=timezone.now(),
                company=default_company
            )
            testing_account_b.set_password(TESTING_ACCOUNT_B_PASSWORD)
            testing_account_b.save()
            self.stdout.write(self.style.SUCCESS('Successfully created testing account B'))
        
        # C
        name_c = lower_and_underescore(TESTING_ACCOUNT_C)

        try:
            testing_account_c = User.objects.get(
                email=f'{name_c}@{name_c}.pt'
            )
            
            self.stdout.write(self.style.SUCCESS('Account C already exists'))
        except User.DoesNotExist:
            testing_account_c = User(
                name=name_c,
                email=f'{name_c}@{name_c}.pt',
                birth_date=timezone.now(),
                company=default_company
            )
            testing_account_c.set_password(TESTING_ACCOUNT_C_PASSWORD)
            testing_account_c.save()
            self.stdout.write(self.style.SUCCESS('Successfully created testing account C'))
    
    