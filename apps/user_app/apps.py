from django.apps import AppConfig

class UserAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user_app'
    verbose_name = "User App"
    
    def ready(self):
        # this is loading the signals   
        from apps.user_app.signals import nullify_user_in_outstanding_tokens
