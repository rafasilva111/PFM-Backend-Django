###
# General imports
##

## Default
import json

## Django
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.timesince import timesince

## Celery
from celery.result import AsyncResult
from celery.app.control import Control

## Django Celery Beat
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule

### App-specific imports

## Models
from apps.common.models import BaseModel
from apps.user_app.models import User

## Tasks and Functions
from apps.task_app.tasks import _launch_task
from apps.task_app.functions import delete_task_logs
from config.celery import app


### Models

class BaseTask(BaseModel):
    """
    Abstract base model for tasks with a specific task type.

    Attributes:
        type (str): The type of task, chosen from 'EMPTY', 'SMALL', 'MEDIUM', or 'LARGE'.
    """

    class TaskType(models.TextChoices):
        EMPTY = 'EMPTY', 'Empty'
        SMALL = 'SMALL', 'Small'
        MEDIUM = 'MEDIUM', 'Medium'
        LARGE = 'LARGE', 'Large'
        FAILURE = 'FAILURE', 'Failure'
    
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
    Abstract base class for conditions used to control job/task execution.

    This is meant to be inherited by specific condition types like
    `TimeCondition` and `MaxRecordsCondition`.
    """
    
    class Meta:
        abstract = True 


class TimeCondition(Condition):
    """
    Condition based on a time schedule, using `CrontabSchedule` for scheduling.

    Attributes:
        crontab (models.ForeignKey): Foreign key to a `CrontabSchedule` instance.
        periodic_task (models.OneToOneField): One-to-one relationship with a `PeriodicTask` instance, can be null or blank.
    """

    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.CASCADE, null=True, blank=True)

    
    def __str__(self):
        return f"{self.id} - Time Condition: {self.periodic_task.crontab}"


class ThresholdCondition(Condition):
    """
    Condition based on a threshold value.

    Attributes:
        threshold_value (int): The threshold value for the condition.
    """
    threshold_value = models.IntegerField()
    
    def __str__(self):
        return f"{self.id} - Threshold Condition: {self.threshold_value}"


class Job(BaseTask):
    """
    Represents a job within the system, inheriting from `BaseTask`.

    Attributes:
        name (str): The name of the job, must be unique.
        company (ForeignKey): The associated company user.
        log_path (str): Path for log storage.
        enabled (bool): Whether the job is enabled.
        parent_task (ForeignKey): The task related to this job.
        parent_job (ForeignKey): Reference to a parent job.
        starting_condition (GenericForeignKey): Condition to start the job.
        stopping_condition (GenericForeignKey): Condition to stop the job.
        debug_mode (bool): Whether the job is in debug mode.
        last_run (DateTime): Last run time of the job.
    """
    name = models.CharField(max_length=255, verbose_name="Job Name", unique=True)
    log_path = models.CharField(max_length=255)
    
    starting_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='start_condition_type', null=True)
    starting_condition_id = models.PositiveIntegerField(null=True)
    starting_condition = GenericForeignKey('starting_condition_type', 'starting_condition_id')
    
    stopping_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='stop_condition_type', null=True)
    stopping_condition_id = models.PositiveIntegerField(null=True)
    stopping_condition = GenericForeignKey('stopping_condition_type', 'stopping_condition_id')

    continue_mode = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    enabled = models.BooleanField(default=True)
    
    @property
    def last_run(self):
        """
        Returns the last finished date of the tasks associated with this job.
        """
        last_task = self.tasks.filter(status=Task.Status.FINISHED).order_by('-finished_at').first()
        return last_task.finished_at if last_task else None

    @property
    def started_run_humanized(self):
        """
        Returns the last finished date of the tasks associated with this job in a human-readable format.
        """
        

        return timesince(self.created_at) + " ago"


    class Meta:
        permissions = [
            ("can_view_job", "Can view Job's details"),
            ("can_view_jobs", "Can view Jobs list"),
            ("can_create_job", "Can create Job"),
            ("can_edit_job", "Can edit Job"),
            
            ("can_pause_job", "Can pause Job"),
            ("can_resume_job", "Can resume Job"),
            ("can_delete_job", "Can delete Job"),
        ]
    

    def delete(self, *args, **kwargs):
        """
        Deletes the job and its associated periodic task and conditions if they exist.
        """

        if self.stopping_condition:
            self.stopping_condition.delete()
        if self.starting_condition:
            self.starting_condition.delete()
        
        super().delete(*args, **kwargs)

    def pause(self):
        """
        Pauses the periodic task and the task associated with this job.
        """

        self.enabled = False
        if self.starting_condition and isinstance(self.starting_condition, TimeCondition):
            self.starting_condition.periodic_task.enabled = False
            self.starting_condition.periodic_task.save()
        self.save()

    def resume(self):
        """
        Resumes the periodic task associated with this job.
        """
        self.enabled = True
        if self.starting_condition and isinstance(self.starting_condition, TimeCondition):
            self.starting_condition.periodic_task.enabled = True
            self.starting_condition.periodic_task.save()
        self.save()

    def __str__(self):
        return f"Job: {self.id} - {self.name}"



class Task(BaseTask):
    """
    Represents an individual task within a job, inheriting from `BaseTask`.

    Attributes:
        started_at (DateTime): The start time of the task.
        stopped_at (DateTime): The time when the task was paused/stopped.
        resumed_at (DateTime): The time when the task was resumed.
        finished_at (DateTime): The time when the task was finished.
        log_path (str): Path for log storage.
        celery_task_id (str): Celery task ID.
        job (ForeignKey): The job associated with this task.
        debug_mode (bool): Whether the task is in debug mode.
        status (str): Status of the task, e.g., STARTING, RUNNING, CANCELED.
    """
    started_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True,blank=True)
    stopped_at = models.DateTimeField(null=True,blank=True)
    log_path = models.CharField(max_length=255, null=True, blank=True)
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True, related_name='tasks')
    debug_mode = models.BooleanField(default=False)
    step = models.IntegerField(default=1)
    
    class Status(models.TextChoices):
        STARTING = 'STARTING', 'Starting'
        PAUSED = 'PAUSED', 'Paused'
        RUNNING = 'RUNNING', 'Running'
        CANCELED = 'CANCELED', 'Canceled'
        STOPPED = 'STOPPED', 'Stopped' # Stop is used when the task is stopped by as Stopping condition
        FAILED = 'FAILED', 'Failed'
        FINISHED = 'FINISHED', 'Finished'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.STARTING,
    )
    
    
    class Meta:
        permissions = [
            ("can_view_task", "Can view Task's details"),
            ("can_view_tasks", "Can view Tasks list"),
            ("can_create_task", "Can create Task"),
            ("can_edit_task", "Can edit Task"),
            
            ("can_restart_task", "Can restart Task"),
            ("can_pause_task", "Can pause Task"),
            ("can_resume_task", "Can resume Task"),
            ("can_cancel_task", "Can cancel Task"),
            ("can_delete_task", "Can delete Task"),
        ]
    
    def __str__(self):
        return f"Task: {self.id} - {self.type}"
    
    @property
    def started_run_humanized(self):
        """
        Returns the last finished date of the tasks associated with this job in a human-readable format.
        """


        if self.started_at:
            teste = timesince(self.started_at)
            return timesince(self.started_at) + " ago"
        
        return "Never"

    def launch(self, continue_mode= False):
        """
        Launches the task by setting its status and initiating a Celery task.
        """
        
        self.status = Task.Status.STARTING
        self.save()
        
        if self.debug_mode:
            _launch_task(self.id, continue_mode)
        else:
            celery_id = CeleryTask.objects.create(
                task=self, 
                celery_task_id=_launch_task.delay(self.id, continue_mode).id
            )
            celery_id.save()
            
        
        
    def purge(self):
        """
        Deletes task logs associated with this task.
        """
        delete_task_logs(self)
            
    def restart(self):
        """
        Restarts the task by resetting and relaunching it.
        """
        if self.status == Task.Status.RUNNING:
            self.kill_current_celery_task()
        
        # reset milestones
        self.step = 1
        self.started_at = timezone.now()
        self.finished_at = None
        self.save()
        self.purge()
        self.launch()
                
    def cancel(self):
        """
        Cancels the task by revoking the Celery task and updating the status.
        """
        # stop celery task
        self.kill_current_celery_task()
        
        self.status = Task.Status.CANCELED
        self.finished_at = timezone.now()
        self.save()

    
    def pause(self):
        if self.status == Task.Status.RUNNING:
            # stop celery task
            self.kill_current_celery_task()
            self.stopped_at = timezone.now()
            self.status = Task.Status.PAUSED
            self.save()

        
    def resume(self):
        
        if self.status == Task.Status.PAUSED or self.status == Task.Status.STOPPED:

            self.resumed_at = timezone.now()
            self.save()
            self.launch(continue_mode=True)
            
    def stop(self):
        if self.status == Task.Status.RUNNING:
            # stop celery task
            self.kill_current_celery_task()
            self.stopped_at = timezone.now()
            self.status = Task.Status.STOPPED
            self.save()

    
    def change_status(self, status):
        
        if status == Task.Status.PAUSED:
            self.pause()
        elif status == Task.Status.CANCELED:
            self.cancel()
        elif status == Task.Status.STOPPED:
            self.stop()
        elif status == Task.Status.RUNNING or status == Task.Status.STARTING:
            self.restart()
        elif status == Task.Status.FINISHED:
            self.finish()
        elif status == Task.Status.FAILED:
            self.fail()
        
    
    def finish(self):
        self.finished_at = timezone.now()
        self.status = Task.Status.FINISHED
        self.kill_current_celery_task()
        self.save()
    
    def fail(self):
        self.finished_at = timezone.now()
        self.status = Task.Status.FAILED
        self.kill_current_celery_task()
        self.save()
        
    def kill_current_celery_task(self):
        """
        Kills the task by revoking the Celery task
        """
        # stop celery task
        result = AsyncResult(self.celery_tasks.last().celery_task_id, app=app)
        result.revoke(terminate=True)
        
    
    
            
class CeleryTask(models.Model):
    """
    Celery task ID model.
    """
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, blank=True, null=True, related_name='celery_tasks')
    
    def __str__(self):
        return f"Celery Task ID: {self.celery_task_id}"