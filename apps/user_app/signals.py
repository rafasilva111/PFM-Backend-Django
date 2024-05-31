# signals.py

from django.db.models.signals import post_delete,pre_delete,post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from apps.user_app.models import Follow

User = get_user_model()

@receiver(post_delete, sender=User)
def nullify_user_in_outstanding_tokens(sender, instance, **kwargs):
    teste = OutstandingToken.objects.filter(user=instance)
    teste.update(user=None)
    
@receiver(post_delete, sender=Follow)
def pre_delete_handler(sender, instance, **kwargs):
    instance.followed.followers_c -=1
    instance.follower.follows_c -=1
    instance.followed.save()
    instance.follower.save()

@receiver(post_save, sender=Follow)
def post_create_handler(sender, instance, created, **kwargs):
    if created:
        # Increment follows
        
        instance.followed.followers_c +=1
        instance.follower.follows_c +=1
        instance.followed.save()
        instance.follower.save()