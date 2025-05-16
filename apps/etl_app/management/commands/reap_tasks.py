from django.core.management.base import BaseCommand

from apps.etl_app.models import Task
from apps.etl_app.tasks import _reap_zombie_tasks

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        
        _reap_zombie_tasks()
        self.stdout.write(self.style.SUCCESS('Zombie tasks reaped successfully'))


