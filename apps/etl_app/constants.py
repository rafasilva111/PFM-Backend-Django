import os

from flask_marshmallow import Marshmallow
from peewee import SqliteDatabase
from django.conf import settings
from django.db import models

""" Main Dirs """




""" Main Database """

main_db = "./recipe/transform/transform_recipes.db"

""" Secondary Databases """


""" 
    Continente
    
"""

""" Ingredients """

""" Extract """

extract_continente_ingredients_db = f"{settings.BASE_DIR}/apps/etl_app/ingredient/extract/continente/dbs"
continente_ingredients_images_folder = f"{settings.BASE_DIR}/apps/etl_app/ingredient/extract/continente/images"

""" Recipes """

extract_continente_recipes_db = f"{settings.BASE_DIR}/apps/etl_app/recipe/extract/continente/dbs"
continente_recipes_images_folder = f"{settings.BASE_DIR}/apps/etl_app/recipe/extract/continente/images"






""" Pingo Doce """

extract_recipe_pingo_doce = "./recipe/extract/pingo_doce/dbs"
extract_recipe_pingo_doce_db = SqliteDatabase(extract_recipe_pingo_doce)


""" Images Dict """

PINGO_DOCE_IMAGES_FOLDER = f"{settings.BASE_DIR}/apps/etl_app/recipe/extract/pingo_doce/images"

""" Marshmallow """

ma = Marshmallow()

""" Constants """

DEFAULT_RECIPE_DIR="recipes/"
DEFAULT_INGREDIENTS_DIR="ingredients/"


class Measures(models.IntegerChoices):
    SOUP_SPOON = 20, 'Soup Spoon'
    TEA_SPOON = 5, 'Tea Spoon'
    DESERT_SPOON = 10, 'Desert Spoon'


