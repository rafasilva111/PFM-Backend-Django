from django.core.management.base import BaseCommand
from apps.user_app.models import User,Company
from apps.common.tests.constants import *

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

        # Create predefined users 
        for name, is_staff, is_superuser, password, user_type in [
            (TESTING_ACCOUNT_PLACEHOLDER, False, False, TESTING_ACCOUNT_PLACEHOLDER_PASSWORD, User.UserType.PLACEHOLDER),
            (TESTING_ACCOUNT_COMPANY, False, False, TESTING_ACCOUNT_COMPANY_PASSWORD, User.UserType.COMPANY),
            (TESTING_ACCOUNT_NORMAL, False, False, TESTING_ACCOUNT_NORMAL_PASSWORD, User.UserType.NORMAL),
            (TESTING_ACCOUNT_COMPANY_STAFF, True, False, TESTING_ACCOUNT_COMPANY_STAFF_PASSWORD, User.UserType.COMPANY_STAFF),
            (TESTING_ACCOUNT_COMPANY_ADMIN, True, False, TESTING_ACCOUNT_COMPANY_ADMIN_PASSWORD, User.UserType.COMPANY_ADMIN),
            (TESTING_ACCOUNT_APP_ADMIN, True, True, TESTING_ACCOUNT_APP_ADMIN_PASSWORD, User.UserType.APP_ADMIN),
            (TESTING_ACCOUNT_APP_STAFF, True, False, TESTING_ACCOUNT_APP_STAFF_PASSWORD, User.UserType.APP_STAFF),
        ]:
            user, created = User.objects.get_or_create(
                name=name,
                email=f"{name}@{name}.pt",
                is_staff=is_staff,
                is_superuser=is_superuser,
                type=user_type
            )
        
            if created:
                user.set_password(password)
                user.save()
        
                self.stdout.write(self.style.SUCCESS(f'User "{name}" created successfully.'))
            else:
                self.stdout.write(self.style.WARNING(f'User "{name}" already exists.'))
    
    