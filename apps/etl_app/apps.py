from django.apps import AppConfig
from django.conf import settings
from os import makedirs
from celery.signals import task_postrun

class EtlAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.etl_app'
    
    def ready(self):
        
        # Import task Signals
        
        from apps.etl_app.signals import post_create_task_handler,post_delete_task_handler,task_success_handler
        
        # create etl logs base dir
        
        makedirs(settings.JOBS_LOG_DIR, exist_ok=True)
        makedirs(settings.TASKS_LOG_DIR, exist_ok=True)