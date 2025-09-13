###
# General imports
##

## Django Signals
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

## Celery Signals
from celery.signals import task_failure

## Models
from apps.etl_app.models import Task
from apps.etl_app.functions import configure_task_logging

import logging

logger = logging.getLogger('django')

@receiver(post_delete, sender=Task)
def post_delete_task_handler(sender, instance, **kwargs):
    """
    Signal handler triggered after a Task instance is deleted.

    - This will automatically purge the task's logs and related data.

    Args:
        sender (Model): The model class that sent the signal (Task).
        instance (Task): The instance of the model that was deleted.
        kwargs (dict): Additional keyword arguments.
    """
    instance.purge()


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **other_kwargs):
    """
    Signal handler for Celery task failure events.

    - Sets the status of the Task to FAILED if the task fails during execution.

    Args:
        sender (Task): The task class that failed.
        task_id (str): ID of the failed Celery task.
        exception (Exception): The exception raised by the task.
        args (tuple): Positional arguments passed to the task.
        kwargs (dict): Keyword arguments passed to the task.
        traceback (Traceback): Traceback of the exception.
        einfo (ExceptionInfo): Exception information.
        extra (dict): Additional keyword arguments.
    """

    logger.warning(f'Task {task_id} failed', exc_info=(type(exception), exception, traceback))
    if task_id:
        task = Task.objects.get(celery_task_id=task_id)
        task.finished_at = timezone.now()
        task.status = Task.Status.FAILED
        task.save()
        
        job_logger, log_info_path = configure_task_logging(task)
        job_logger.error(f'Task {task_id} failed', exc_info=(type(exception), exception, traceback))
        
        channel_layer = get_channel_layer()
    
        async_to_sync(channel_layer.group_send)(
            f"task_{task.id}",  # Room group name
            {
                'type': 'celery_task_update',  # The name of the method in the consumer to call
                'status': task.status,
                'finished_at': task.finished_at.strftime('%d de %B de %Y às %H:%M')
            })


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


from celery.signals import task_success
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Celery task success signal handler
@task_success.connect
def task_success_handler(sender, result, **kwargs):
    
    logger.info(f'Success: {sender.request.id}')
    try:
        task = Task.objects.get(celery_task_id=sender.request.id)
    except Task.DoesNotExist: # This might happen when Job is triggered
        return

    # Send the message to the appropriate WebSocket group (task-specific group)
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
            f"task_{task.id}",  # Room group name
            {
                'type': 'celery_task_update',  # The name of the method in the consumer to call
                'task': task.status,
            }
        )
    
    " Trigger all the tasks that depend on this task "
    dependent_task_awaiter_triggered = task.dependent_tasks_awaiter.all()
    for dependent_task_awaiter in task.dependent_tasks_awaiter.all():
        if dependent_task_awaiter.dependent_task.status == Task.Status.WAITING:
            dependent_task_awaiter.dependent_task.launch()
            dependent_task_awaiter_triggered.filter(dependent_task=dependent_task_awaiter.dependent_task).delete()
            
        elif dependent_task_awaiter.dependent_task.status == Task.Status.PAUSED:
            dependent_task_awaiter.dependent_task.resume()
            dependent_task_awaiter.delete()
            dependent_task_awaiter_triggered.filter(dependent_task=dependent_task_awaiter.dependent_task).delete()
        else:
            logger.warning(f"Task {dependent_task_awaiter.dependent_task.id} is not in a state to be launched or resumed.")
        
    


@receiver(post_delete, sender=Task)
def delete_issue_if_no_tasks(sender, instance, **kwargs):
    """
    Signal handler that deletes issues associated with the given instance if they have no related tasks.

    Args:
        sender (Model): The model class that sent the signal.
        instance (Model instance): The instance whose issues are being checked.
        **kwargs: Additional keyword arguments passed by the signal.

    Behavior:
        Iterates through all issues related to the instance. If an issue has no associated tasks,
        it is deleted from the database.
    """

    for issue in instance.issues.all():
        if issue.task.count() == 0:
            issue.delete()