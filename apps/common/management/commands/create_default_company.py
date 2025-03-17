from django.core.management.base import BaseCommand
from apps.user_app.models import Company
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET

class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):
        

        # Goodbites Account
        
        default_company_account, created = Company.objects.get_or_create(
            name=f'Goodbites',
            defaults={
                'imgs_bucket': f"{FIREBASE_STORAGE_COMPANY_BUCKET}/Goodbites",
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created testing account A'))
        else:
            self.stdout.write(self.style.SUCCESS('Account A already exists'))
            

        