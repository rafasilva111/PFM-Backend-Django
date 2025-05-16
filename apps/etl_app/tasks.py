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
from apps.etl_app.functions import configure_task_logging, configure_job_logging
from apps.common.models import ProcessType
from apps.etl_app.recipe.extract.main import _extract_recipes
from apps.etl_app.recipe.transform.main import _transform_recipes
from apps.etl_app.recipe.load.main import __load_recipes
#from apps.etl_app.recipe.load.main import _load_recipes

from apps.etl_app.ingredient.extract.main import _extract_ingredients
#from apps.etl_app.ingridients.transform.main import _transform_ingridients
#from apps.etl_app.ingredients.load.main import _load_ingridients

# Set up main logger
main_logger = logging.getLogger('django')


###
# Job Task Functions
##

@app.task
def _launch_job(job_id, force_start=False):
    """
    Initializes a job, creating or resuming associated tasks as needed.

    - If a job has no associated tasks, it will create a new one.
    - If the last task is paused, it resumes that task.
    - If the last task is finished, it creates a new task.
    
    Args:
        job_id (int): ID of the Job to initialize.
    """
    from apps.etl_app.models import Job, Task, JobTriggerHistory, TaskStatusConditionAwaiter
    
    # Assert the job trigger
    if force_start:
        job_trigger_type = JobTriggerHistory.Type.FORCE_START
    else:
        job_trigger_type = JobTriggerHistory.Type.STARTING_CONDITION
    
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        main_logger.error(f'Job {job_id} does not exist')
        return

    if not job.enabled and not force_start:
        return

    # Configure job-specific logging
    job_logger, job.log_path = configure_job_logging(job)
    job.save()

    # Determine the status of the last task
    job_logger.info(f'')
    job_logger.info(f'')
    job_logger.info(f'Job Starting Condition triggered.')
    job_logger.info(f'')

    current_task = job.current_task
    job_logger.info(f'Checking for existing tasks...')
    
    " Check if job has starting condition "
    if current_task is None:
        job_logger.info(f'No existing task. Creating new task.')
        job_trigger_action = JobTriggerHistory.Action.CREATE_TASK
        
    elif current_task.status == Task.Status.FINISHED:
        job_logger.info(f'Task {current_task.id} has Finished. Creating new task...')
        job_trigger_action = JobTriggerHistory.Action.CREATE_TASK
        
    elif current_task.status == Task.Status.PAUSED:
        job_logger.info(f'Task {current_task.id} is Paused. Resuming task...')
        job_trigger_action = JobTriggerHistory.Action.RESUME_TASK
        
    elif current_task.status == Task.Status.FAILED and force_start:
        job_logger.info(f'Task {current_task.id} has Failed. Creating new task...')
        job_trigger_action = JobTriggerHistory.Action.CREATE_TASK
    
    else: # If the task is running or starting, we don't want to start a new job
        job_logger.info(f'Job {job_id} was not started due to Task {current_task.id} with status {current_task.status}.')
        return

    " Persist a Job Trigger History "
    job.create_job_trigger_history(
        type = job_trigger_type,
        action = job_trigger_action
    )
    
    
    
    
    if job_trigger_action == JobTriggerHistory.Action.CREATE_TASK:
        
        " Create a new task if the last task was finished or if there was no task "
        current_task = Task.objects.create(
            type=job.type,
            parent_job=job,
            company=job.company,
            process=job.process
        )
        
        " Assert if parent task is running and if it is add job to the awaiting queue "
        if (job.parent_task and job.parent_task.status == Task.Status.RUNNING) or (job.parent_job and job.parent_job.is_current_task_running()):
            
            
            if job.parent_job:
                task_condition_waiter, created = TaskStatusConditionAwaiter.objects.get_or_create(
                    dependent_task=current_task,
                    owner_task=job.parent_job.current_task,
                )
                
                
                job_logger.warning(f'Task {current_task.id} was created but not launched due to Parent Job {job.parent_job.id} with status {job.parent_job.current_task.status}.')
            else:
                task_condition_waiter, created = TaskStatusConditionAwaiter.objects.get_or_create(
                    dependent_task=current_task,
                    owner_task=job.parent_task,
                )
                
                job_logger.warning(f'Task {current_task.id} was not resumed due to Parent Task {job.parent_task.id} with status {job.parent_task.status}.')
                
            if created:
                job_logger.info(f'Added to the awaiting queue.')
            else:
                job_logger.warning(f'Already in the awaiting queue. Skipping task launch.')
        else:
            " Launch the task "
            current_task.launch()
            
            job_logger.info(f'')
            job_logger.info(f'Task {current_task.id} created.')
        
    elif job_trigger_action == JobTriggerHistory.Action.RESUME_TASK:
        
        " Assert if parent task is running and if it is add job to the awaiting queue "
        if (job.parent_task and job.parent_task.status == Task.Status.RUNNING) or (job.parent_job and job.parent_job.is_current_task_running()):
            
            if job.parent_job:
                task_condition_waiter, created = TaskStatusConditionAwaiter.objects.get_or_create(
                    dependent_task=current_task,
                    owner_task=job.parent_job.current_task,
                )
                
                
                job_logger.warning(f'Task {current_task.id} was created but not launched due to Parent Job {job.parent_job.id} with status {job.parent_job.current_task.status}.')
            else:
                task_condition_waiter, created = TaskStatusConditionAwaiter.objects.get_or_create(
                    dependent_task=current_task,
                    owner_task=job.parent_task,
                )
                
                job_logger.warning(f'Task {current_task.id} was not resumed due to Parent Task {job.parent_task.id} with status {job.parent_task.status}.')
                
            if created:
                job_logger.info(f'Added to the awaiting queue.')
            else:
                job_logger.warning(f'Already in the awaiting queue. Skipping task launch.')
                
            if created:
                job_logger.info(f'Added to the awaiting queue.')
            else:
                job_logger.warning(f'Already in the awaiting queue.')
        else:
            
            " Resume the task "
            current_task.resume()
            
            job_logger.info(f'')
            job_logger.info(f'Task {current_task.id} resumed.')
    
    

    
    
        
@app.task
def _stop_job(job_id):
    
    from apps.etl_app.models import Job, Task

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        main_logger.error(f'Job {job_id} does not exist')
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
    

    job_logger.info(f'Pausing current active Task ( {current_task.id} ).')
    current_task.pause()
    job_logger.info(f'')
    job_logger.info(f'Task {current_task.id} Paused.')


    

###
# Task Functions
##

@app.task
def _launch_task(task_id, resume=True):
    """
    Launches a specific task, running a test task based on the task type.

    - Configures logging and updates task status to RUNNING.
    - Initiates a test task with varying counts based on task type.

    Args:
        task_id (int): ID of the Task to launch.
    """
    from apps.etl_app.models import Task

    task = Task.objects.get(id=task_id)

    logger, task.log_path = configure_task_logging(task)
    task.status = Task.Status.RUNNING
    task.save()

    # Determine task behavior based on task type
    
    logger.info("")
    if resume:
        logger.info(f'Resuming {task.type} Task')   
    else:
        logger.info(f'Starting {task.type} Task')
    
    logger.info("")
    
    match task.type:
        case Task.TaskType.TEST:
            max_count = 10
            test_task(logger, task, max_count, resume)
            
        case Task.TaskType.EMPTY:
            max_count = 1
            test_task(logger, task, max_count, resume)
            
        case Task.TaskType.FAILURE:
            max_count = -1
            test_task(logger, task, max_count, resume)
        
        case Task.TaskType.MID_FAILURE:
            max_count = -10
            test_task(logger, task, max_count, resume)
            
                
        case Task.TaskType.EXTRACT:

            match task.process:
                case ProcessType.INGREDIENTS:
                    _extract_ingredients(logger,task, resume)
                case ProcessType.RECIPES:
                    _extract_recipes(logger, task, resume)
                
        case  Task.TaskType.TRANSFORM:
            
            logger.info('Starting data Transform')
            
            match task.process:
                case ProcessType.INGREDIENTS:
                    logger.info('Yet to be done')
                    pass
                case ProcessType.RECIPES:
                    _transform_recipes(logger, task, resume)
    
        case Task.TaskType.LOAD:
            
            
            match task.process:
                case ProcessType.INGREDIENTS:
                    logger.info('Yet to be done')
                    pass
                case ProcessType.RECIPES:
                    __load_recipes(logger, task, resume)
                
        case Task.TaskType.FULL_PROCESS:
                    
            match task.process:
                case ProcessType.INGREDIENTS:
                    logger.info('Yet to be done')
                    pass
                case ProcessType.RECIPES:
                    #__extract_recipes(logger,task)
                    #__transform_recipes(logger,task)
                    #__load_recipes(logger,task)
                    logger.info('Yet to be done')
                    
                    pass
                                



###
# Helper Functions
##

def test_task(logger, task, max_count=10000, continue_mode=True):
    """
    A helper function to simulate task processing by counting to a max value.

    - Logs each count increment and the task start/completion.
    - If max_count == -1, raises an exception to simulate a failure.

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
    
    trigger_failure = False
    
    if max_count == -1:
        trigger_failure = True

    elif max_count < -1:
        max_count = - max_count
        trigger_failure = True
        

    counter = task.step if continue_mode else 0
    

    while counter < max_count:
        counter += 1
        logger.info(f"Counting at: {counter} .")
        
        time.sleep(1)
        # Save state to avoid losing the counter value in case of failure or pause
        task.step = counter
        task.save()
    
    # Check if a failure was triggered
    if trigger_failure:
        logger.info("Failure was triggered.")
        raise Exception("Failure was triggered.")
    
    logger.info("")
    logger.info("Done...")
    logger.info("")
    
    # Update task status to finished
    task.finish()

def _reap_zombie_tasks():
    """
    Reaps zombie tasks that have been running for too long.
    
    - This function checks for tasks that have been running for more than 24 hours
    and sets their status to FAILED.
    """
    from apps.etl_app.models import Task


    from config.celery import app
    
    # Get the list of active Celery tasks
    i = app.control.inspect()
    active = i.active()
    active_celery_tasks_ids = []
    if active:
        for worker, tasks in active.items():
            for task in tasks:
                active_celery_tasks_ids.append(task['id'])
    
    # Get current running tasks from the database
    tasks = Task.objects.filter(status=Task.Status.RUNNING)
    
    active_sql_tasks_ids = []
    for task in tasks:
        if task.celery_task_id:
            active_sql_tasks_ids.append(task.celery_task_id)

    # Calculate the Zombie tasks
    zombie_tasks = list(set(active_sql_tasks_ids) - set(active_celery_tasks_ids))
    
    # Find all tasks that have been running for more than 24 hours
    zombie_tasks = Task.objects.filter(
        celery_task_id__in=zombie_tasks,
    )

    # Update the status of each zombie task to FAILED
    for task in zombie_tasks:
        task.pause()
    
    return len(zombie_tasks)