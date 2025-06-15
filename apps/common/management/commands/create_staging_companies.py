from django.core.management.base import BaseCommand
from apps.common.models import ProcessType
from apps.user_app.models import Company,User
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET,COMPANY_PINGO_DOCE,COMPANY_CONTINENTE,COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD, COMPANY_IMAGES_ROOT_PATH
from apps.common.functions import lower_and_underescore, send_image_to_firebase
from django.utils import timezone


PROFILE_IMAGE_NAME = "profile_image.png"

class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):

        ## Pingo Doce

        # Check for Company Model
        username = lower_and_underescore(COMPANY_PINGO_DOCE)      
        company_images_bucket = f"{FIREBASE_STORAGE_COMPANY_BUCKET}{username}"
        
        try:
            pingo_doce_company = Company.objects.get(name=COMPANY_PINGO_DOCE)

        except Company.DoesNotExist:

            name = COMPANY_PINGO_DOCE
            pingo_doce_company = Company.objects.create(
                name=COMPANY_PINGO_DOCE,
                imgs_bucket=company_images_bucket
                )
            self.stdout.write(self.style.SUCCESS(f'Successfully created the {COMPANY_PINGO_DOCE} company'))

        # Check for Company default User
        pingo_doce_image_path = f"{company_images_bucket}/{PROFILE_IMAGE_NAME}"
        pingo_doce_user, created = User.objects.get_or_create(
            username=username,
            email=f'{username}@example.com',
            type=User.UserType.COMPANY,
            defaults={
                'name': COMPANY_PINGO_DOCE,
                'password': COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,
                'verified': True,
                'birth_date': timezone.now(),
                'company': pingo_doce_company,
                'image':pingo_doce_image_path
            }
        )

        user_image_path = f"{COMPANY_IMAGES_ROOT_PATH}{username}/{PROFILE_IMAGE_NAME}"
        send_image_to_firebase(
            image_content=open(user_image_path, "rb").read(),
            image_destination=pingo_doce_image_path
        )
        pingo_doce_user.image = pingo_doce_image_path
        pingo_doce_user.save()

        pingo_doce_user.user_account = pingo_doce_user
        pingo_doce_user.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully created the {COMPANY_PINGO_DOCE} company default user'))



        ## Continente

        # Check for Company Model
        username = lower_and_underescore(COMPANY_CONTINENTE)      
        company_images_bucket = f"{FIREBASE_STORAGE_COMPANY_BUCKET}{username}"
        
        try:
            continente_company = Company.objects.get(name=COMPANY_CONTINENTE)

        except Company.DoesNotExist:

            name = COMPANY_CONTINENTE
            continente_company = Company.objects.create(
                name='Continente',
                imgs_bucket=company_images_bucket
                )
            continente_company.processes = [ProcessType.INGREDIENTS, ProcessType.RECIPES]
            continente_company.save()
            self.stdout.write(self.style.SUCCESS('Successfully created the default company'))

        # Check for Company default User
        username = lower_and_underescore(COMPANY_CONTINENTE)  
        company_image_path = f"{company_images_bucket}/{PROFILE_IMAGE_NAME}"
        
        continente_user, created = User.objects.get_or_create(
            username=username,
            email=f'{username}@example.com',
            type=User.UserType.COMPANY,
            defaults={
                'name': COMPANY_CONTINENTE,
                'password': COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD,
                'verified': True,
                'birth_date': timezone.now(),
                'company': continente_company,
                'image':user_image_path
            }
        )
        
        user_image_path = f"{COMPANY_IMAGES_ROOT_PATH}{username}/{PROFILE_IMAGE_NAME}"
        send_image_to_firebase(
            image_content=open(user_image_path, "rb").read(),
            image_destination=company_image_path
        )
        continente_user.image = company_image_path
        continente_user.save()
        
        continente_company.user_account = continente_user
        continente_company.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully created/updated the {COMPANY_CONTINENTE} company default user'))
        

