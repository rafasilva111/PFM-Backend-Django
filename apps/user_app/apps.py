from django.apps import AppConfig

class UserAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user_app'
    verbose_name = "User App"
    
    def ready(self):
        # this is loading the signals   
        pass
        import apps.user_app.signals
