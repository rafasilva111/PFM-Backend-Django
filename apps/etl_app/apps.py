from django.apps import AppConfig
from django.conf import settings
from os import makedirs

from .constants import ETL_EXTRACT_LOG_DIR, ETL_TRANSFORM_LOG_DIR,ETL_LOAD_LOG_DIR,ETL_FULL_PROCESS_LOG_DIR

class EtlAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.etl_app'
    
    def ready(self):
        from .signals import post_create_task_handler
        
        # create etl logs base dir
        
        makedirs(settings.ETL_LOG_DIR, exist_ok=True)
        makedirs(ETL_EXTRACT_LOG_DIR, exist_ok=True)
        makedirs(ETL_TRANSFORM_LOG_DIR, exist_ok=True)
        makedirs(ETL_LOAD_LOG_DIR, exist_ok=True)
        makedirs(ETL_FULL_PROCESS_LOG_DIR, exist_ok=True)

