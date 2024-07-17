from django.apps import AppConfig
from django.conf import settings
import os
import firebase_admin
from firebase_admin import credentials,storage

class DashboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

cred = credentials.Certificate(os.path.join(settings.BASE_DIR, 'apps/common/keys/projetofoodmanager-firebase.json'))
firebase_admin.initialize_app(cred, {
    'storageBucket': 'projetofoodmanager.appspot.com'
})

# Path to your local image file
