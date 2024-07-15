import json
import uuid
from datetime import time, datetime

import requests

from apps.etl_app.constants import extract_recipe_pingo_doce
from apps.etl_app.recipe.extract.pingo_doce.models import BaseModel,Recipe, Tag, NutritionInformation, Ingredient, \
    Recipe_links,database_proxy,IngredientQuantity
from peewee import SqliteDatabase



RecipeTagThrough = Recipe.tags.get_through_model()

models_ = [Recipe, Tag, NutritionInformation, Ingredient,IngredientQuantity, RecipeTagThrough, Recipe_links]


def start_recipe_extract_db(logger, task, reset=False):
    """
    Start the recipe extract database.

    Args:
        logger (logging.Logger): The logger object.
        task (Task): The task object.
        reset (bool, optional): Whether to reset the database. Defaults to False.

    Returns:
        SqliteDatabase: The new database instance.
    """
    
    # Log the start of the recipe extract database
    logger.info("Starting Recipe Extract Database...")
    
    # Save the task with the new sql file name
    task_sql_file = f"{extract_recipe_pingo_doce}/db_{task.id}.sql"

    from apps.etl_app.models import TaskType
    
    if task.type == TaskType.FULL_PROCESS:
        task.extract_sql_file = task_sql_file
    else:
        task.sql_file = task_sql_file

    task.save()

    # Create a new database instance
    extract_recipe_pingo_doce_db = SqliteDatabase(task_sql_file)    
    
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    database_proxy.initialize(extract_recipe_pingo_doce_db)
    
    # Connect to the database
    extract_recipe_pingo_doce_db.connect()
    
    # If reset is True, drop all tables in the database
    if reset:
        logger.info("Reseting Database...")
        extract_recipe_pingo_doce_db.drop_tables(models_)
    
    # Create all tables in the database
    extract_recipe_pingo_doce_db.create_tables(models_)
    
    # Return the new database instance
    return extract_recipe_pingo_doce_db
