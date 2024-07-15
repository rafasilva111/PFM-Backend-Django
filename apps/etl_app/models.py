from django.db import models

# Create your models here.


from django.db import models
from datetime import datetime
from apps.common.models import BaseModel
from apps.user_app.models import User
from django.utils import timezone
from apps.etl_app.tasks import _launch_task
from apps.etl_app.functions import delete_task_logs,delete_task_database
from celery.result import AsyncResult
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from celery.app.control import Control
import json
from config.celery import app

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

###
#
#   Task
#
##

class TaskType(models.TextChoices):
        EXTRACT = 'EXTRACT', 'Extract'
        TRANSFORM = 'TRANSFORM', 'Transform'
        LOAD = 'LOAD', 'Load'
        FULL_PROCESS = 'FULL_PROCESS', 'Full Process'


class BaseTask(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    max_records = models.IntegerField(default=None, null=True, blank=True)
    type = models.CharField(
        max_length=12,
        choices=TaskType.choices,
        default=None,
        null=True
    )

    

    class Meta:
        abstract = True



class Job(BaseTask):
    name = models.CharField(max_length=255)
    crontab = models.OneToOneField(CrontabSchedule, on_delete=models.CASCADE)
    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.CASCADE, null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    

    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks')


    def save(self, *args, **kwargs):
        super(Job, self).save(*args, **kwargs)

        if not self.periodic_task:
            # Create or get the crontab schedule (it needs to be done here and not in form because of the args where we need the job id)
            periodic_task, created = PeriodicTask.objects.get_or_create(
                crontab=self.crontab,
                name=self.name,
                task='apps.etl_app.tasks._init_job',
                args=json.dumps([self.id]),
            )

            self.periodic_task = periodic_task
        # Save the model instance again to store the periodic_task relation
        super(Job, self).save(*args, **kwargs)
        

        

    def delete(self, *args, **kwargs):
        # Delete the associated PeriodicTask and CrontabSchedule
        if self.periodic_task:
            self.periodic_task.delete()
        if self.crontab:
            self.crontab.delete()
        
        # Call the superclass delete method
        super().delete(*args, **kwargs)

    def pause_task(self):
        if self.periodic_task:
            self.periodic_task.enabled = False
            self.periodic_task.save()

    def resume_task(self):
        if self.periodic_task:
            self.periodic_task.enabled = True
            self.periodic_task.save()


class Task(BaseTask):
    started_at = models.DateTimeField(auto_now=True)
    paused_at = models.DateTimeField(null=True)
    resumed_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    log_path = models.CharField(max_length=255, null=True, blank=True)
    sql_file = models.CharField(max_length=255, null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='subtasks')
    
    extract_sql_file = models.CharField(max_length=255, null=True, blank=True)
    transform_sql_file = models.CharField(max_length=255, null=True, blank=True)
    
    
    
    
    class Status(models.TextChoices):
        STARTING = 'STARTING', 'Starting'
        RUNNING = 'RUNNING', 'Running'
        PAUSED = 'PAUSED', 'Paused'
        CANCELED = 'CANCELED', 'Canceled'
        FAILED = 'FAILED', 'Failed'
        FINISHED = 'FINISHED', 'Finished'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.STARTING,
    )

    def launch(self):
        if self.status == Task.Status.CANCELED:
            return
        
        self.status = Task.Status.STARTING
        
        self.celery_task_id = _launch_task.delay(self.id).id

        self.save()
    
    def purge(self):
        
        delete_task_logs(self)
        delete_task_database(self)

    
    def start(self):

        self.started_at = timezone.now()
        self.save()

        if self.status != Task.Status.RUNNING:
            self.launch()
            
            
            
              
    def restart(self):

        self.started_at = timezone.now()
        self.save()

        if self.status != Task.Status.CANCELED:
            self.purge()


        self.launch()
            

    def pause(self):
        
        # stop celery task
        result = AsyncResult(self.celery_task_id, app=app)
        result.revoke(terminate=True)

        
        self.paused_at = timezone.now()
        self.status = Task.Status.PAUSED
        self.save()

        
    def resume(self):
        if self.status == Task.Status.PAUSED:

            self.resumed_at = timezone.now()
            self.save()

            self.launch()


    
    def cancel(self):
        
        # stop celery task
        result = AsyncResult(self.celery_task_id, app=app)
        result.revoke(terminate=True)
        
        self.status = Task.Status.CANCELED
        self.finished_at = timezone.now()
        self.save()

