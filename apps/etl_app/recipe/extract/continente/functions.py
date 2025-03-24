import logging
import re
from apps.etl_app.functions import start_extract_db


#from apps.etl_app.functions import print_it
from apps.etl_app.recipe.extract.continente.models import Recipe, Tag, NutritionInformation, Ingredient, \
    Recipe_links, database_proxy

RecipeTagThrough = Recipe.tags.get_through_model()

models_ = [Recipe, Tag, NutritionInformation, Ingredient, RecipeTagThrough, Recipe_links]


def start_recipe_extract_db(path, logger, task, reset=False):
    """
    Start the recipe extract database.

    Args:
        logger (logging.Logger): The logger object.
        task (Task): The task object.
        reset (bool, optional): Whether to reset the database. Defaults to False.

    Returns:
        SqliteDatabase: The new database instance.
    """
    
    
    return start_extract_db(path, logger, task, reset, models_)


# Regular expression pattern for separating quantity, unit, and ingredient
pattern = re.compile(r'(\d+)\s*(c\. [a-zA-Z]+|c\. sopa|c\. chá|ml|g)?\s*(.*)')

# Function to separate elements
def separate_unit_title(title):
    match = pattern.match(title)
    if match:
        quantity = match.group(1)
        unit = match.group(2)
        ingredient = match.group(3)
        return quantity, unit, ingredient
    else:
        return None

