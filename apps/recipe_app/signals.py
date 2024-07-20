from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.recipe_app.models import RecipeAuditLog

@receiver(post_save)
def create_audit_log(sender, instance, created, **kwargs):
    # Check if the instance has a custom attribute 'audit_log_user'
    manual_user = getattr(instance, 'audit_log_user', None)
    
    if created:
        user = manual_user or getattr(instance, 'user', None)
        
        for field in instance._meta.fields:
            field_name = field.name
            new_value = getattr(instance, field_name, None)
            
            RecipeAuditLog.objects.create(
                model_name=sender.__name__,
                field_name=field_name,
                old_value=None,
                new_value=new_value,
                user=user,
            )
