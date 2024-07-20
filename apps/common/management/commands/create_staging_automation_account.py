from django.core.management.base import BaseCommand
from apps.user_app.models import Company,User
from apps.common.constants import AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD,AUTOMATION_ACCOUNT
from apps.common.functions import lower_and_underescore
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):

        ## Automation Account

        try:
            automation_account = User.objects.get(
                username=lower_and_underescore(AUTOMATION_ACCOUNT),
                email = f'{lower_and_underescore(AUTOMATION_ACCOUNT)}@example.com'
                )

        except Company.DoesNotExist:

            automation_account, created = User.objects.get_or_create(
                username=lower_and_underescore(AUTOMATION_ACCOUNT),
                email=f'{lower_and_underescore(AUTOMATION_ACCOUNT)}@example.com',
                user_type=User.UserType.COMPANY,
                defaults={
                    'name': AUTOMATION_ACCOUNT,
                    'password': AUTOMATION_ACCOUNT_DEFAULT_USER_PASSWORD,
                    'verified': True,
                    'birth_date': timezone.now(),
                }
            )
            self.stdout.write(self.style.SUCCESS('Successfully created the default company'))


