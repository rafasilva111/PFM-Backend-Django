from celery import shared_task
from os import makedirs
from datetime import datetime
from django.utils import timezone
from apps.etl_app.functions import configure_task_logging,configure_job_logging
from config.celery import app



#from apps.etl_app.recipe.extract.continente.main import __extract_continente
from apps.etl_app.recipe.extract.pingo_doce.main import __extract_pingo_doce
from apps.etl_app.recipe.transform.main import __transform_recipes
from apps.etl_app.recipe.load.main import __load_recipes

from apps.common.constants import COMPANY_PINGO_DOCE

import logging

main_logger = logging.getLogger('django')

###
#
#   Job
#
##

@app.task
def _init_job(job_id):
    from .models import Job, MaxRecordsCondition
    from .models import Task
    

    # Get Job
    
    try:
        job = Job.objects.get(id = job_id)
    except Job.DoesNotExist:
        main_logger.error(f'Job {job_id} does not exist')
        return
    
    job.last_run = timezone.now()
    job.save()
    
    job_logger, log_info_path = configure_task_logging(job)
    job.log_path = log_info_path
    
    # Deal with Starting the Tasks
    # Job should start a new task if none have ever started
    # Job should continue with an existing task if one has been started
    
    job_logger.info(f'Job {job_id} was started.')
    
    try:
        current_task = job.tasks.order_by('-created_at').first()
        job_logger.info(f'Current Task: {current_task}')
    except:
        current_task = None

        
    
    
    if current_task is None:
        job_logger.info(f'No existing task. Creating new task.')
        
    
    elif current_task.status == Task.Status.FINISHED:
        job_logger.info(f'Task {current_task.id} has finished. Creating new task.')
        
    elif current_task.status == Task.Status.PAUSED:
        current_task.resume()
        
        return
    else:
        main_logger.info(f'Job {job_id} was not started because of Task\'s ({current_task.id}) with status {current_task.status}.')
        
        return
    
    # Check if there is a stopping condition for the job    
    stopping_condition_max_records = None
    if isinstance(job.starting_condition, MaxRecordsCondition):
        stopping_condition_max_records = job.starting_condition.max_records
        job_logger.info(f'Task has a stopping condition: {stopping_condition_max_records}')
    
    task = Task.objects.create(
            company = job.company, 
            type = job.type, 
            parent_task = job.parent_task,
            job = job, 
            stopping_condition_max_records = stopping_condition_max_records
            )
        
    job_logger.info(f'Starting task {task.id}')
    task.start()
    
    


###
#
#   ETL
#
##


 
###
#
#   Recipe ETL
#
##       
        
"""
@app.task
def _extract_recipes(task_id,logger = None):
    from .models import Task,TaskType
    
    task = Task.objects.get(id = task_id)
    logger, log_folder = configure_logging(task)
    
    task.log_path = log_folder
    task.status = Task.Status.RUNNING
    task.save()
"""
    
       
        
"""@app.task
def _transform_recipes(task_id,logger = None):
    from .models import Task,TaskType
    
    task = Task.objects.get(id = task_id)

    logger, log_folder = configure_logging(task)
    task.log_path = log_folder

    task.status = Task.Status.RUNNING
    task.save()

    logger.info('Starting data Transform')
    
    __transform_recipes(logger,task)"""
    
    

"""@app.task
def _load_recipes(task_id,logger = None):
    from .models import Task
    
    task = Task.objects.get(id = task_id)

    if not logger:
        logger, log_folder = configure_logging(task)
        task.log_path = log_folder

    task.status = Task.Status.RUNNING
    task.save()

    logger.info('Starting data Load')
    
    __load_recipes(logger,task)"""

"""@app.task
def _full_process(task_id):
    from .models import Task

    task = Task.objects.get(id = task_id)
    logger, log_folder = configure_logging(task)

    task.save()

    _extract_recipes(task_id,logger)

    _transform_recipes(task_id,logger)

    _load_recipes(task_id,logger)"""


@app.task
def _launch_task(task_id):
    from .models import Task, TaskType

    task = Task.objects.get(id = task_id)


    logger, log_info_path = configure_task_logging(task)
    task.log_path = log_info_path

    task.status = Task.Status.RUNNING

    task.save()

    

    if task.type == TaskType.EXTRACT:

        logger.info('Starting data Extract')

        if task.company.name == COMPANY_PINGO_DOCE:
            __extract_pingo_doce(logger,task)

    elif task.type == TaskType.TRANSFORM:

        logger.info('Starting data Transform')
    
        __transform_recipes(logger,task)

    elif task.type == TaskType.LOAD:
        logger.info('Starting data Load')
    
        __load_recipes(logger,task)
    
    elif task.type == TaskType.FULL_PROCESS:
        __extract_pingo_doce(logger,task)

        __transform_recipes(logger,task)

        __load_recipes(logger,task)



###
#
#   Recipe ETL
#
##

"""def _extract_ingredients(continente=True, new_copy=False):

            #Extractce
            #:param continente: if True, it will extract all recipes from continente
            #:param new_copy: if True, it will create a new copy of the database, saving the old one


    print_it(f"Extracting all ingredients...")
    print_it()
    print_it()

    if continente:
        __extract_ingredients_continente(max_ingredients=-1, continue_mode=True, new_copy=new_copy)"""



@app.task
def test_task():
    print("Test Task Executed")

