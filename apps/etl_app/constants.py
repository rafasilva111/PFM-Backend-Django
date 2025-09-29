import os

from flask_marshmallow import Marshmallow
from peewee import SqliteDatabase
from django.conf import settings
from django.db import models


##
# Task's logging configuration
#

JOBS_LOG_DIR = "apps/etl_app/logs/jobs"
TASKS_LOG_DIR = "apps/etl_app/logs/tasks"


""" Main Database """

main_db = "./recipe/transform/transform_recipes.db"

""" Secondary Databases """



""" 
        Extract 

"""

"""    Continente   """


""" Ingredients """

EXTRACT_CONTINENTE_INGREDIENTS_DB = f"apps/etl_app/ingredient/extract/continente/dbs"
CONTINENTE_INGREDIENTS_IMAGES_FOLDER = f"apps/etl_app/ingredient/extract/continente/images"


""" Recipes """

EXTRACT_CONTINENTE_RECIPES_DB = f"apps/etl_app/recipe/extract/continente/dbs"
CONTINENTE_RECIPES_IMAGES_FOLDER = f"apps/etl_app/recipe/extract/continente/images"


""" Pingo Doce """

""" Ingredients """

extract_recipe_pingo_doce = "./recipe/extract/pingo_doce/dbs"


""" 
        Transform 

"""

"""    Continente   """

"""     Recipes     """

TRANSFORM_CONTINENTE_RECIPES_DB = f"apps/etl_app/recipe/transform/continente/dbs"






""" Images Dict """

PINGO_DOCE_IMAGES_FOLDER = f"apps/etl_app/recipe/extract/pingo_doce/images"

""" Marshmallow """

ma = Marshmallow()

""" Constants """

DEFAULT_RECIPE_DIR="recipes/"
DEFAULT_INGREDIENTS_DIR="ingredients/"


class Measures(models.IntegerChoices):
    SOUP_SPOON = 20, 'Soup Spoon'
    TEA_SPOON = 5, 'Tea Spoon'
    DESERT_SPOON = 10, 'Desert Spoon'


eu_reference_intake = {
    "energy_kcal": 2000,
    "carbohydrates_g": 260,
    "sugars_g": 90,
    "fat_g": 70,
    "saturates_g": 20,
    "protein_g": 50,
    "salt_g": 6
}