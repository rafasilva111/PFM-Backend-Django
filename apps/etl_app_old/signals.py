# signals.py

from django.db.models.signals import post_delete,post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Task
import os
import shutil

@receiver(post_save, sender=Task)
def post_create_task_handler(sender, instance, created, **kwargs):
    if created:
        # Increment follows
        instance.start()

@receiver(post_delete, sender=Task)
def post_delete_task_handler(sender, instance, **kwargs):
    instance.purge()