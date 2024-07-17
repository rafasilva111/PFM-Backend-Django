from peewee import SqliteDatabase

# Transform Models
from apps.etl_app.recipe.transform.models import database_proxy as transform_database_proxy

def start_recipe_extract_db(logger, task):

    
    # Log the start of the recipe extract database
    logger.info("Starting Recipe Transform Database...")
    
    from apps.etl_app.models import TaskType

    if task.type == TaskType.FULL_PROCESS:
        task_sql_file = task.transform_sql_file 
    else:
        task_sql_file = task.sql_file

    # Create a new database instance
    transform_recipes_db = SqliteDatabase(task_sql_file)    
    
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    transform_database_proxy.initialize(transform_recipes_db)
    
    # Connect to the database
    transform_recipes_db.connect()
    
    # Return the new database instance
    return transform_recipes_db









