# signals.py

from django.db.models.signals import post_delete,pre_delete,post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
#from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from django.contrib.auth.models import  Group
User = get_user_model()

