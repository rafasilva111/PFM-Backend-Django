from django.db import models

# Create your models here.


from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from datetime import datetime
from apps.common.models import BaseModel
from apps.user_app.models import Company,User
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
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=12,
        choices=TaskType.choices,
        default=None,
        null=True
    )

    

    class Meta:
        abstract = True

class Condition(models.Model):
    """
    Abstract base class for different types of conditions.
    """    
    class Meta:
        abstract = True 
    
    


class TimeCondition(Condition):
    """
    Condition based on a time schedule using Crontab.
    """
    crontab = models.ForeignKey(
        CrontabSchedule,
        on_delete=models.CASCADE,
    )
    
    def __str__(self):
        """
        Override the default string representation of the task.
        """
        return f"{self.id} - Crontab: {self.crontab} "


class MaxRecordsCondition(Condition):
    """
    Condition based on a maximum number of records.
    """
    max_records = models.IntegerField(null=True)

    def __str__(self):
        """
        Override the default string representation of the task.
        """
        return f"{self.id} - Max Records: {self.max_records} "

class Job(BaseTask):
    name = models.CharField(max_length=255, verbose_name="Job Name",unique=True)    
    company = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs', verbose_name="Company")
    
    log_path = models.CharField(max_length=255)
    
    enabled = models.BooleanField(default=True)
     
    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='jobs')
    parent_job = models.ForeignKey('Job', on_delete=models.SET_NULL, blank=True, null=True, related_name='child_jobs')
    
    # GenericForeignKey to reference either TimeCondition
    starting_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='start_condition_type', null=True)
    starting_condition_id = models.PositiveIntegerField(null=True)
    starting_condition = GenericForeignKey('starting_condition_type', 'starting_condition_id')
    
    # GenericForeignKey to reference either TimeCondition or MaxRecordsCondition
    stopping_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='stop_condition_type', null=True)
    stopping_condition_id = models.PositiveIntegerField(null=True)
    stopping_condition = GenericForeignKey('stopping_condition_type', 'stopping_condition_id')

    
    
    debug_mode = models.BooleanField(default=False) 
    
    last_run = models.DateTimeField(null=True, blank=True)

        
    def delete(self, *args, **kwargs):
        # Delete the stopping condition if it exists
        if self.stopping_condition:
            self.stopping_condition.delete()
        
        # Similarly, delete the starting condition if needed
        if self.starting_condition:
            self.starting_condition.delete()
        
        # Call the superclass's delete method to handle the deletion of the Job instance
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
    job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True, related_name='tasks')
    
    company = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    
    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='subtasks')
    
    stopping_condition_max_records = models.IntegerField(default=None, null=True, blank=True)
    
    extract_sql_file = models.CharField(max_length=255, null=True, blank=True)
    transform_sql_file = models.CharField(max_length=255, null=True, blank=True)
    
    debug_mode = models.BooleanField(default=False)
    
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
    
    def __str__(self):
        """
        Override the default string representation of the task.
        """
        return f"Task: {self.id} - {self.type}"

    def launch(self):
        if self.status == Task.Status.CANCELED:
            return
        
        self.status = Task.Status.STARTING
        
        if self.debug_mode:
            _launch_task(self.id)
        
        else:
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

