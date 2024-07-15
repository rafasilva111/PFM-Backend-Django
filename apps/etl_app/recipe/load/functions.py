import json
import os
import time
import uuid

import firebase_admin
import requests
from firebase_admin import credentials, initialize_app, storage

#from classes import RecipeSchema
#from constants import ROOT_EMAIL, ROOT_PASSWORD, SERVER_URL
#from functions import print_it, get_user_token, send_image_to_firebase
#from recipe.transform.models import Recipe



"""def start_firebase():
    cred = credentials.Certificate("pfm-firebase-sdk.json")
    initialize_app(cred, {
        'storageBucket': 'projetofoodmanager.appspot.com'  # Replace with your project's storage bucket URL
    })


def close_firebase():
    firebase_admin.delete_app(firebase_admin.get_app())


def generate_image_name():
    # Generate a unique image name using a timestamp and random component
    timestamp = int(time.time())
    random_suffix = str(uuid.uuid4().hex[:6])  # Generate a 6-character random string
    image_name = f"image_{timestamp}_{random_suffix}.jpg"
    return image_name


def create_company_account(email = "pingo_doce@company.com", password = "password"):
    token = get_user_token(email =ROOT_EMAIL, password=ROOT_PASSWORD)
    headers = {
        "Authorization": f"Bearer {str(token['token'])}"
    }

    image_name = 'images/company/pingo_doce/profile/profile_image.jpg'

    data = {
        "name": "Pingo Doce",
        "username": "PingoDoce",
        "birth_date": "15/3/2000",
        "email": email,
        "password": password,
        "img_source": image_name
    }

    send_image_to_firebase(image_destination=image_name,
                           image_source='avatar_images/pingo_doce/profile_image.jpg')

    response = requests.post(url=f"http://{SERVER_URL}/api/v1/admin/company", headers=headers, json=data)

    if response.status_code == 409 or response.status_code == 201:
        return email, password
    else:
        raise Exception("Unable to create company profile.")"""


from peewee import SqliteDatabase

# Transform Models
from apps.etl_app.recipe.transform.models import database_proxy as transform_database_proxy

def start_recipe_extract_db(logger, task):

    
    # Log the start of the recipe extract database
    logger.info("Starting Recipe Transform Database...")
    
    from apps.etl_app.models import TaskType

    if task.type == TaskType.FULL_PROCESS:
        task_sql_file = task.transform_sql_file 
    else:
        task_sql_file = task.sql_file

    # Create a new database instance
    transform_recipes_db = SqliteDatabase(task_sql_file)    
    
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    transform_database_proxy.initialize(transform_recipes_db)
    
    # Connect to the database
    transform_recipes_db.connect()
    
    # Return the new database instance
    return transform_recipes_db









