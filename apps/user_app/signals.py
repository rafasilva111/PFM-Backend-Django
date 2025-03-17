# signals.py

from django.db.models.signals import post_delete,pre_delete,post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
#from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from django.contrib.auth.models import  Group
User = get_user_model()

@receiver(post_save, sender=User)
def add_user_to_default_group(sender, instance, created, **kwargs):
    
    if created:  
        group_name = "Normal"  
        group, created = Group.objects.get_or_create(name=group_name)  
        instance.groups.add(group)