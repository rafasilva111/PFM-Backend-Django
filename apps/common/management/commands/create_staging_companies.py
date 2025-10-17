from django.core.management.base import BaseCommand
from apps.common.models import ProcessType
from apps.user_app.models import Company, User
from apps.common.constants import (
    FIREBASE_STORAGE_COMPANY_BUCKET,
    COMPANY_PINGO_DOCE,
    COMPANY_CONTINENTE,
    COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,
    COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD,
    COMPANY_IMAGES_ROOT_PATH
)
from apps.common.functions import lower_and_underscore, send_image_to_firebase
from django.utils import timezone
from pathlib import Path

PROFILE_IMAGE_NAME = "profile_image.png"

# Define companies configuration in a dict for scalability
COMPANIES_CONFIG = [
    {
        "name": COMPANY_PINGO_DOCE,
        "default_password": COMPANY_PINGO_DOCE_DEFAULT_USER_PASSWORD,
        "processes": [],
    },
    {
        "name": COMPANY_CONTINENTE,
        "default_password": COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD,
        "processes": [ProcessType.INGREDIENTS, ProcessType.RECIPES],
    },
]

class Command(BaseCommand):
    help = "Create default companies and their users if they do not exist"

    def handle(self, *args, **kwargs):
        for company_config in COMPANIES_CONFIG:
            self.create_company_and_user(company_config)

    def create_company_and_user(self, config):
        username = lower_and_underscore(config["name"])
        company_bucket = f"{FIREBASE_STORAGE_COMPANY_BUCKET}{username}"
        user_image_path = f"{COMPANY_IMAGES_ROOT_PATH}{username}/{PROFILE_IMAGE_NAME}"
        company_image_path = f"{company_bucket}/{PROFILE_IMAGE_NAME}"

        # Create or get Company
        company, created = Company.objects.get_or_create(
            name=config["name"],
            defaults={"imgs_bucket": company_bucket}
        )

        # Assign processes if specified
        if config["processes"]:
            company.processes = config["processes"]
            company.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created company: {config['name']}"))

        # Create or get default User
        user, created_user = User.objects.get_or_create(
            username=username,
            email=f"{username}@example.com",
            type=User.UserType.COMPANY,
            defaults={
                "name": config["name"],
                "password": config["default_password"],
                "verified": True,
                "profile_type": User.ProfileType.PUBLIC,
                "birth_date": timezone.now(),
                "company": company,
                "image": company_image_path
            }
        )

        # Upload image to Firebase
        if Path(user_image_path).exists():
            send_image_to_firebase(
                image_content=open(user_image_path, "rb").read(),
                image_destination=company_image_path
            )
            user.image = company_image_path
            user.save()

        # Link company and user
        company.user_account = user
        company.save()

        self.stdout.write(self.style.SUCCESS(f"Created/updated default user for {config['name']}"))
