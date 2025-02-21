from django.core.management.base import BaseCommand

from apps.task_app.models import Task
from apps.task_app.tasks import _init_job

class Command(BaseCommand):
    help = 'Starts an existing job by it\'s ID'
    
    def add_arguments(self, parser):
        parser.add_argument('id', type=int, help='ID of the Task to start')

    def handle(self, *args, **kwargs):
        
        if kwargs['id'] is None:
            self.stdout.write(self.style.ERROR('Error: Task ID is required'))
            return

        id = kwargs['id']
        ## Automation Account

        try:
            task = Task.objects.get(id = id)

        except Task.DoesNotExist:
            self.stdout.write(self.style.SUCCESS('Error: Task does not exist'))
        
        task.start()


