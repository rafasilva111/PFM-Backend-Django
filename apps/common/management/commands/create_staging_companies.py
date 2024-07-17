from django.core.management.base import BaseCommand
from apps.user_app.models import Company,User
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET,COMPANY_PINGO_DOCE,COMPANY_CONTINENTE,COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD
from apps.common.functions import lower_and_underescore
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):

        ## Pingo Doce

        # Check for Company Model

        try:
            pingo_doce_company = Company.objects.get(name=COMPANY_PINGO_DOCE)

        except Company.DoesNotExist:

            name = COMPANY_PINGO_DOCE
            pingo_doce_company = Company.objects.create(
                name=COMPANY_PINGO_DOCE,
                email=f'{lower_and_underescore(name)}@example.com',
                imgs_bucket=f"{FIREBASE_STORAGE_COMPANY_BUCKET}/{lower_and_underescore(name)}"
                )
            self.stdout.write(self.style.SUCCESS(f'Successfully created the {COMPANY_PINGO_DOCE} company'))

        # Check for Company default User

        if not pingo_doce_company.user_account:

            pingo_doce_user, created = User.objects.get_or_create(
                username=lower_and_underescore(COMPANY_PINGO_DOCE),
                email=f'{lower_and_underescore(COMPANY_PINGO_DOCE)}@example.com',
                user_type=User.UserType.COMPANY,
                defaults={
                    'name': COMPANY_PINGO_DOCE,
                    'password': COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,
                    'verified': True,
                    'birth_date': timezone.now(),
                }
            )
            
            pingo_doce_company.user_account = pingo_doce_user
            pingo_doce_company.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully created the {COMPANY_PINGO_DOCE} company default user'))



        ## Continente

        # Check for Company Model
        
        try:
            continente_company = Company.objects.get(name=COMPANY_CONTINENTE)

        except Company.DoesNotExist:

            name = COMPANY_CONTINENTE
            continente_company = Company.objects.create(
                name='Continente',
                email=f'{lower_and_underescore(name)}@example.com',
                imgs_bucket=f"{FIREBASE_STORAGE_COMPANY_BUCKET}/{lower_and_underescore(name)}"
                )
            self.stdout.write(self.style.SUCCESS('Successfully created the default company'))

        # Check for Company default User
        
        if not continente_company.user_account:
            
            continente_user, created = User.objects.get_or_create(
                username=lower_and_underescore(COMPANY_CONTINENTE),
                email=f'{lower_and_underescore(COMPANY_CONTINENTE)}@example.com',
                user_type=User.UserType.COMPANY,
                defaults={
                    'name': COMPANY_CONTINENTE,
                    'password': COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD,
                    'verified': True,
                    'birth_date': timezone.now(),
                }
            )
            
            continente_company.user_account = continente_user
            continente_company.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully created the {COMPANY_PINGO_DOCE} company default user'))
        

