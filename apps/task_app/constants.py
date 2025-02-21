import os

from flask_marshmallow import Marshmallow
from peewee import SqliteDatabase
from django.conf import settings
from django.db import models

""" Main Dirs """




""" Main Database """

main_db = "./recipe/transform/transform_recipes.db"

""" Secondary Databases """

extract_recipe_pingo_doce = f"{settings.BASE_DIR}/apps/etl_app/recipe/extract/pingo_doce/dbs"


transform_recipe = f"{settings.BASE_DIR}/apps/etl_app/recipe/transform/dbs"


extract_ingredient_continente = "./ingredient/extract/continente" \
                            "/extract_ingredients.db "

extract_ingredient_continente_db = SqliteDatabase(extract_ingredient_continente)



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


