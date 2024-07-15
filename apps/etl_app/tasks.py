from celery import shared_task
from os import makedirs
from datetime import datetime
from apps.etl_app.functions import configure_logging
from config.celery import app


#from apps.etl_app.recipe.extract.continente.main import __extract_continente
from apps.etl_app.recipe.extract.pingo_doce.main import __extract_pingo_doce
from apps.etl_app.recipe.transform.main import __transform_recipes
from apps.etl_app.recipe.load.main import __load_recipes


###
#
#   Job
#
##

@app.task
def _init_job(job_id):
    from .models import Job
    from .models import Task
    print("here")
    try:
        job = Job.objects.get(id = job_id)
    except Job.DoesNotExist:
        print(job_id)
        return
    task = Task.objects.create(user = job.user, max_records= job.max_records, type = job.type, parent_task = job.parent_task, job = job )
    task.save()
    
    job.last_run = datetime.now()
    job.save()

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

    logger, log_folder = configure_logging(task)
    task.log_path = log_folder

    task.status = Task.Status.RUNNING

    task.save()

    

    if task.type == TaskType.EXTRACT:

        logger.info('Starting data Extract')

        if task.user.username == "Pingo Doce":
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
