###
# General Imports
##

## Django Utilities
from django.utils import timezone

## Celery App
from config.celery import app

## Standard Libraries
import time
import logging

### App-specific imports

## Functions
from apps.task_app.functions import configure_task_logging, configure_job_logging

# Set up main logger
main_logger = logging.getLogger('django')


###
# Job Task Functions
##

@app.task
def _launch_job_task(job_id):
    """
    Initializes a job, creating or resuming associated tasks as needed.

    - If a job has no associated tasks, it will create a new one.
    - If the last task is paused, it resumes that task.
    - If the last task is finished, it creates a new task.
    
    Args:
        job_id (int): ID of the Job to initialize.
    """
    from apps.task_app.models import Job, Task

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        main_logger.error(f'Job {job_id} does not exist')
        return

    if not job.enabled:
        return

    # Configure job-specific logging
    job_logger, job.log_path = configure_job_logging(job)
    job.save()

    # Determine the status of the last task
    job_logger.info(f'')
    job_logger.info(f'')
    job_logger.info(f'Job Starting Condition triggered.')
    job_logger.info(f'')
    
    # Check if the job is in continue mode, which means resuming the last task if it exists
    current_task = job.tasks.order_by('-created_at').first()
    job_logger.info(f'Checking for existing tasks...')
    
    if job.continue_mode:
        if current_task is None:
            job_logger.info(f'No existing task. Creating new task.')
        elif current_task.status == Task.Status.FINISHED:
            job_logger.info(f'Task {current_task.id} has finished. Creating new task.')
        elif current_task.status == Task.Status.PAUSED:
            job_logger.info(f'Task {current_task.id} has been resumed.')
            current_task.resume()
            return
        else:
            job_logger.info(f'Job {job_id} was not started due to Task {current_task.id} with status {current_task.status}.')
            return
    else:
        job_logger.info(f'Creating new task.')

    task = Task.objects.create(
        type=job.type,
        job=job,
    )
    task.save()
    
    # You dont need to call the launch method here, the signal will do it for you
    job_logger.info(f'')
    job_logger.info(f'Task {task.id} created.')
    
        
@app.task
def _stop_job_task(job_id):
    
    from apps.task_app.models import Job, Task

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        main_logger.error(f'Job {job_id} does not exist')
        return

    if not job.enabled:
        return

    # Configure job-specific logging
    job_logger, job.log_path = configure_job_logging(job)
    job.save()

    # Get the current task
    current_task = job.tasks.order_by('-created_at').first()
    
    # Determine the status of the last task
    job_logger.info(f'')
    job_logger.info(f'')
    job_logger.info(f'Job Stopping Condition triggered.')
    job_logger.info(f'')
    
    if job.continue_mode:
        job_logger.info(f'Pausing current active Task ( {current_task.id} ).')
        current_task.pause()
        job_logger.info(f'')
        job_logger.info(f'Task {current_task.id} Stopped.')
    else:
        job_logger.info(F'Stopping current active Task ( {current_task.id} ).')
        current_task.stop()
        job_logger.info(f'')
        job_logger.info(f'Task {current_task.id} Stopped.')

    

###
# Task Functions
##

@app.task
def _launch_task(task_id, continue_mode=True):
    """
    Launches a specific task, running a test task based on the task type.

    - Configures logging and updates task status to RUNNING.
    - Initiates a test task with varying counts based on task type.

    Args:
        task_id (int): ID of the Task to launch.
    """
    from apps.task_app.models import Task

    task = Task.objects.get(id=task_id)

    logger, log_info_path = configure_task_logging(task)
    task.log_path = log_info_path
    task.status = Task.Status.RUNNING
    task.save()

    # Determine task behavior based on task type
    match task.type:
        case Task.TaskType.SMALL:
            max_count = 5
        case Task.TaskType.MEDIUM:
            max_count = 1000
        case Task.TaskType.LARGE:
            max_count = 10000
        case Task.TaskType.EMPTY:
            max_count = 1
        case Task.TaskType.FAILURE:
            max_count = -1
            
    logger.info("")
    if continue_mode:
        logger.info(f'Resuming {task.type} Task')   
    else:
        logger.info(f'Starting {task.type} Task')
    
    test_task(logger, task, max_count, continue_mode)


###
# Helper Functions
##

def test_task(logger, task, max_count=10000, continue_mode=True):
    """
    A helper function to simulate task processing by counting to a max value.

    - Logs each count increment and the task start/completion.
    - If max_count < 0, raises an exception to simulate a failure.

    Args:
        logger (logging.Logger): The logger to use for logging task events.
        task (Task): The task instance associated with the counting.
        max_count (int): The maximum count for the test task. Defaults to 10000.
    
    Raises:
        Exception: If max_count is less than 0.
    """
    logger.info("")
    logger.info("Executing Task...")
    logger.info("")
    
    if max_count < 0:
        raise Exception("Max Count cannot be less than 0")

    counter = task.step if continue_mode else 1

    while counter < max_count:
        logger.info(f"Counting at: {counter}")
        time.sleep(1)
        
        counter += 1
        
        # Save state to avoid losing the counter value in case of failure or pause
        task.step = counter
        task.save()
    
    # Log the final count
    logger.info(f"Counting at: {counter}")

    # Update task status to finished
    task.finished_at = timezone.now()
    task.status = task.Status.FINISHED
    task.save()
    
    logger.info("")
    logger.info("Done...")
    logger.info("")

