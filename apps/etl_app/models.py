###
# General imports
##

from os import path
import shutil
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
from django.conf import settings

### App-specific imports

## Models
from apps.common.models import BaseModel
from apps.user_app.models import Company,User

## Tasks and Functions
from apps.common.models import ProcessType
from apps.etl_app.tasks import _launch_task, _launch_job
from config.celery import app

# Third-party imports
from multiselectfield import MultiSelectField

### Models



###
#
#   Base Models
#
##


class BaseTask(BaseModel):
    """
    Abstract base model for tasks with a specific task type.

    Attributes:
        type (str): The type of task, chosen from 'EMPTY', 'SMALL', 'MEDIUM', or 'LARGE'.
    """
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    

    class TaskType(models.TextChoices):
        """
        Enumeration for different types of ETL tasks.

        Attributes:
            EXTRACT (str): Represents an extraction task.
            TRANSFORM (str): Represents a transformation task.
            LOAD (str): Represents a loading task.
            FULL_PROCESS (str): Represents a full ETL process task.
        """
        EXTRACT = 'EXTRACT', 'Extract'
        TRANSFORM = 'TRANSFORM', 'Transform'
        LOAD = 'LOAD', 'Load'
        FULL_PROCESS = 'FULL_PROCESS', 'Full Process'
        TEST = 'TEST', 'Test'
        FAILURE = 'FAILURE', 'Failure'
        EMPTY = 'EMPTY', 'Empty'
        MID_FAILURE = 'MID_FAILURE', 'Mid Failure'
    
    type = models.CharField(
        max_length=12,
        choices=TaskType.choices,
        default=None,
        null=True
    )
    
    
    process = models.CharField(
        choices=ProcessType.choices,
        max_length=20,  # Adjust based on expected selections
        default=None,
        null=True,
    )
    

    class Meta:
        abstract = True

###
#
#   Conditions Models
#
##

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
    
    def delete(self,*args, **kwargs):
        
        # Delete the periodic task associated with this condition
        if self.periodic_task:
            self.periodic_task.delete()
        
        return super().delete(*args, **kwargs)


class ThresholdCondition(Condition):
    """
    Condition based on a threshold value.

    Attributes:
        threshold_value (int): The threshold value for the condition.
    """
    threshold_value = models.IntegerField()
    
    def __str__(self):
        return f"{self.id} - Threshold Condition: {self.threshold_value}"

class TaskStatusConditionAwaiter(BaseModel):
    
    dependent_task = models.ForeignKey('Task', on_delete=models.CASCADE)
    owner_task = models.ForeignKey('Task', related_name="dependent_tasks_awaiter", on_delete=models.CASCADE)
    triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

###
#
#   Jobs Model
#
##

class JobTriggerHistory(BaseModel):
    """
    Represents the history of job triggers.

    Attributes:
        job (ForeignKey): The job associated with this trigger.
        triggered_at (DateTime): The time when the job was triggered.
        status (str): The status of the job at the time of triggering.
    """
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='trigger_history')
    
    class Type(models.TextChoices):
        """
        Enumeration for different types of ETL tasks.

        Attributes:
            EXTRACT (str): Represents an extraction task.
            TRANSFORM (str): Represents a transformation task.
            LOAD (str): Represents a loading task.
            FULL_PROCESS (str): Represents a full ETL process task.
        """
        STOPPING_CONDITION = 'STOPPING_CONDITION', 'Stopping Condition'
        STARTING_CONDITION = 'STARTING_CONDITION', 'Starting Condition'
        FORCE_START = 'FORCE_START', 'Force Start'
    
    type = models.CharField(
        max_length=18,
        choices=Type.choices,
        default=None,
        null=True
    )
    
    
    class Action(models.TextChoices):
        """
        Enumeration for different types of ETL tasks.

        Attributes:
            EXTRACT (str): Represents an extraction task.
            TRANSFORM (str): Represents a transformation task.
            LOAD (str): Represents a loading task.
            FULL_PROCESS (str): Represents a full ETL process task.
        """
        CREATE_TASK = 'CREATED_TASK', 'Created New Task'
        RESUME_TASK = 'RESUMED_TASK', 'Resumed Task'
        REST = 'REST', 'Rest'
    
    action = models.CharField(
        max_length=12,
        choices=Action.choices,
        default=None,
        null=True
    )
    
    triggered_at = models.DateTimeField(auto_now_add=True)

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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', verbose_name="Company")
    log_path = models.CharField(max_length=255)
    
    starting_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='start_condition_type', null=True)
    starting_condition_id = models.PositiveIntegerField(null=True)
    starting_condition = GenericForeignKey('starting_condition_type', 'starting_condition_id')
    
    stopping_condition_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='stop_condition_type', null=True)
    stopping_condition_id = models.PositiveIntegerField(null=True)
    stopping_condition = GenericForeignKey('stopping_condition_type', 'stopping_condition_id')
    
    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='jobs')
    parent_job = models.ForeignKey('Job', on_delete=models.SET_NULL, blank=True, null=True, related_name='child_jobs')
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    enabled = models.BooleanField(default=True)
    
    @property
    def last_run(self):
        """
        Returns the last finished date of the tasks associated with this job.
        """
        last_task = self.tasks.order_by('-finished_at').first()
        return last_task.finished_at if last_task else None

    @property
    def started_run_humanized(self):
        """
        Returns the last finished date of the tasks associated with this job in a human-readable format.
        """
        

        return timesince(self.created_at) + " ago"

    @property
    def current_task(self):
        """
        Returns the current task associated with this job.
        """
        return self.tasks.last()

    class Meta:
        permissions = [
            ("can_view_job", "Can view Job's details"),
            ("can_view_jobs", "Can view Jobs list"),
            ("can_create_job", "Can create Job"),
            ("can_edit_job", "Can edit Job"),
            
            ("can_force_start_job", "Can force start Job"),
            ("can_enable_job", "Can pause Job"),
            ("can_disable_job", "Can resume Job"),
            ("can_delete_job", "Can delete Job"),
        ]
    
    def is_current_task_running(self):
        """
        Checks if the current task associated with this job is running.
        """

        if self.current_task:
            return self.current_task.status == Task.Status.RUNNING
        return False
    
    def force_start(self):
        _launch_job(self.id, force_start=True)
    
    def delete(self, *args, **kwargs):
        """
        Deletes the job and its associated periodic task and conditions if they exist.
        """
        # Delete the stopping condition if it exists
        if self.stopping_condition:
            self.stopping_condition.delete()
        
        # Similarly, delete the starting condition if needed
        if self.starting_condition:
            self.starting_condition.delete()
        
        # Call the superclass's delete method to handle the deletion of the Job instance
        super().delete(*args, **kwargs)

    def disable(self):
        """
        Pauses the periodic task and the task associated with this job.
        """

        self.enabled = False
        
        " Disable the periodic task if it exists ( aka CrontabSchedule ) "
        if self.starting_condition and isinstance(self.starting_condition, TimeCondition):
            self.starting_condition.periodic_task.enabled = False
            self.starting_condition.periodic_task.save()
            
        self.save()

    def enable(self):
        """
        Resumes the periodic task associated with this job.
        """
        
        self.enabled = True
        
        " Enable the periodic task if it exists ( aka CrontabSchedule ) "
        if self.starting_condition and isinstance(self.starting_condition, TimeCondition):
            self.starting_condition.periodic_task.enabled = True
            self.starting_condition.periodic_task.save()
            
        self.save()

    def create_job_trigger_history(self, type, action):
        
        """
        Creates a new job trigger history entry.
        """
        job_trigger_history = JobTriggerHistory.objects.create(
            job=self,
            type=type,
            action=action
        )
        return job_trigger_history
    
    def __str__(self):
        return f"Job: {self.id} - {self.name}"

###
#
#   Tasks Model
#
##
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
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')

    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True,blank=True)
    paused_at = models.DateTimeField(null=True,blank=True)
    resumed_at = models.DateTimeField(null=True,blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    log_path = models.CharField(max_length=255, null=True, blank=True)
    sql_path = models.CharField(max_length=255, null=True, blank=True)
    
    parent_task = models.ForeignKey('Task', on_delete=models.SET_NULL, blank=True, null=True, related_name='subtasks')
    parent_job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True, related_name='subtasks')
    owner_job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True, related_name='tasks')
    
    debug_mode = models.BooleanField(default=False)
    step = models.IntegerField(default=0)
    
    # Statistics

    links = models.IntegerField(default=0, null=True, blank=True)
        
    items_processed = models.IntegerField(default=0, null=True, blank=True)
    items_expected = models.IntegerField(default=0, null=True, blank=True)
    
    warnings = models.IntegerField(default=0, null=True, blank=True)
    errors = models.IntegerField(default=0, null=True, blank=True)
    
    class Status(models.TextChoices):
        WAITING = 'WAITING', 'Waiting'
        PAUSED = 'PAUSED', 'Paused'
        RUNNING = 'RUNNING', 'Running'
        CANCELED = 'CANCELED', 'Canceled'
        STOPPED = 'STOPPED', 'Stopped' # Stop is used when the task is stopped by as Stopping condition
        FAILED = 'FAILED', 'Failed'
        FINISHED = 'FINISHED', 'Finished'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.WAITING,
    )
    
    
    @property
    def started_run_humanized(self):
        """
        Returns the last finished date of the tasks associated with this job in a human-readable format.
        """

        if self.started_at:
            return timesince(self.started_at) + " ago"
        
        return "Never"
    
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
        """
        Override the default string representation of the task.
        """
        return f"Task: {self.id} - {self.type}"
    
    def get_log_path(self):
        
        """
        Returns the log path for the task.
        """
        
            
        if self.log_path:
            return f"{settings.BASE_DIR}{self.log_path}"
        else:
            return None

    def launch(self, resume = False):
        """
        Launches the task by setting its status and initiating a Celery task.
        """
        
        self.status = Task.Status.WAITING
        self.started_at = timezone.now()
        self.save()
        
        if self.debug_mode:
            _launch_task(self.id, resume)
            # We dont save here otherwise we rollback the task
        else:
            self.celery_task_id = _launch_task.delay(self.id, resume).id
            self.save()
            
        
        
        
    def purge(self):
        """
        Deletes task logs associated with this task.
        """
        
        self.delete_task_logs()
        self.delete_sql_file()
        
        
    def delete_task_logs(self):
        if self.log_path:
            directory_path = path.dirname(self.log_path)

            if path.exists(directory_path):
                shutil.rmtree(directory_path)
            
    def delete_sql_file(self):
        if self.sql_path:
            directory_path = path.dirname(self.sql_path)

            if path.exists(directory_path):
                shutil.rmtree(directory_path)
            
    def restart(self):
        """
        Restarts the task by resetting and relaunching it.
        """

        self.__kill_current_celery_task()
        self.links = 0
        self.items_processed = 0
        self.items_expected = 0
        self.warnings = 0
        self.step = 0 # reset milestones
        self.finished_at = None
        self.save()
        self.purge()
        self.launch()
                
    def cancel(self):
        """
        Cancels the task by revoking the Celery task and updating the status.
        """
        # stop celery task
        self.__kill_current_celery_task()
        
        self.status = Task.Status.CANCELED
        self.finished_at = timezone.now()
        self.save()

    def pause(self):
        if self.status == Task.Status.RUNNING:
            # stop celery task
            self.__kill_current_celery_task()
            self.paused_at = timezone.now()
            self.status = Task.Status.PAUSED
            self.save()

    def resume(self):
        
        if self.status == Task.Status.PAUSED:

            self.resumed_at = timezone.now()
            self.save()
            self.launch(resume=True)
            
    def change_status(self, status):
        
        if status == Task.Status.PAUSED:
            self.pause()
        elif status == Task.Status.CANCELED:
            self.cancel()
        elif status == Task.Status.STOPPED:
            self.stop()
        elif status == Task.Status.RUNNING or status == Task.Status.WAITING:
            self.restart()
        elif status == Task.Status.FINISHED:
            self.finish()
        elif status == Task.Status.FAILED:
            self.fail()
        
    
    def finish(self, kill_celery_task=False):
        self.finished_at = timezone.now()
        self.status = Task.Status.FINISHED
        
        self.__calculate_duration()
        
        if kill_celery_task:
            self.__kill_current_celery_task()
        self.save()
    
    def fail(self):
        self.finished_at = timezone.now()
        self.status = Task.Status.FAILED
        self.__calculate_duration()
        self.__kill_current_celery_task()
        self.save()
    
    def get_type_process_display(self):
        return f"{self.type} - {self.process}"
    
    def __kill_current_celery_task(self):
        """
        Kills the task by revoking the Celery task
        """
        
        if self.celery_task_id:
            result = AsyncResult(self.celery_task_id, app=app)
            result.revoke(terminate=True)
        
        
    
    def __calculate_duration(self):
        """
        Calculate the duration of the task.
        """
        
        if self.finished_at:
            self.duration = self.finished_at - self.started_at
        else:
            self.duration = None



