from django.apps import AppConfig
from os import makedirs
from apps.etl_app.constants import JOBS_LOG_DIR,TASKS_LOG_DIR

class EtlAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.etl_app'
    
    def ready(self):
        
        # Import task Signals
        from apps.etl_app.signals import post_delete_task_handler, task_success_handler

        # create etl logs base dir
        
        makedirs(JOBS_LOG_DIR, exist_ok=True)
        makedirs(TASKS_LOG_DIR, exist_ok=True)