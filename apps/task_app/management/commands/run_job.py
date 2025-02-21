from django.core.management.base import BaseCommand

from apps.task_app.models import Job
from apps.task_app.tasks import _init_job

class Command(BaseCommand):
    help = 'Starts an existing job by it\'s ID'
    
    def add_arguments(self, parser):
        parser.add_argument('id', type=int, help='ID of the job to start')

    def handle(self, *args, **kwargs):
        
        if kwargs['id'] is None:
            self.stdout.write(self.style.ERROR('Error: Job ID is required'))
            return

        id = kwargs['id']
        print(id)
        ## Automation Account

        try:
            job = Job.objects.get(id = id)

        except Job.DoesNotExist:
            self.stdout.write(self.style.SUCCESS('Error: Job does not exist'))
        
        _init_job(job.id)


