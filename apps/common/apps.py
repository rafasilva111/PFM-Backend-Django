from django.apps import AppConfig

#from apps.common.keys.firebase import firebaseConfig
#import pyrebase

class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'

"""firebase = pyrebase.initialize_app(firebaseConfig)

import firebase_admin
from firebase_admin import credentials
import os
# Get the current directory
current_dir = os.path.dirname(__file__) if '__file__' in locals() else os.getcwd()

# Path to service account credentials JSON file
cred_path = os.path.join(current_dir, "keys", "projetofoodmanager-firebase.json")

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)"""