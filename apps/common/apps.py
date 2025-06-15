from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
from django.conf import settings


class DashboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

# Path to your local image file
# Initialize Firebase Admin SDK
cred = credentials.Certificate(f"{settings.BASE_DIR}/apps/common/secrets/project-food-manager-firebase.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'project-food-manager.firebasestorage.app'  # Replace with your actual bucket name
})

