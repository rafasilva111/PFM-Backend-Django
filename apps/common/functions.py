
from firebase_admin import storage
from django.conf import settings
import os


def send_image_to_firebase(image_content, image_destination):

    # Get the bucket object
    bucket = storage.bucket()

    # Create a blob object within the bucket
    blob = bucket.blob(image_destination)

    # Upload the image content directly
    blob.upload_from_string(image_content, content_type='image/jpeg')



def lower_and_underescore(text):
    return text.lower().replace(' ', '_')