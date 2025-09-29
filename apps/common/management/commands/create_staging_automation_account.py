from django.core.management.base import BaseCommand
from apps.user_app.models import Company,User
from apps.common.constants import AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD,AUTOMATION_ACCOUNT
from apps.common.functions import lower_and_underscore
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create the default Automation Account if it does not exist'

    def handle(self, *args, **kwargs):

        automation_account, created = User.objects.get_or_create(
            username=lower_and_underscore(AUTOMATION_ACCOUNT),
            email=f'{lower_and_underscore(AUTOMATION_ACCOUNT)}@example.com',
            type=User.UserType.APP_STAFF,
            defaults={
                'name': AUTOMATION_ACCOUNT,
                'password': AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD,
                'verified': True,
                'birth_date': timezone.now(),
            }
        )
        
        if created:
            automation_account.set_password(AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD)
            automation_account.save()
            self.stdout.write(self.style.SUCCESS(f'Automation Account "{AUTOMATION_ACCOUNT}" created successfully.'))
        else:
            self.stdout.write(self.style.WARNING(f'Automation Account "{AUTOMATION_ACCOUNT}" already exists.'))


