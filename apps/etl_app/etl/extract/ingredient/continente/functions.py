import logging
import re


#from apps.etl_app.functions import print_it
from apps.etl_app.etl.extract.recipe.continente.models import Recipe, Tag, NutritionInformation, Ingredient, \
    Recipe_links

RecipeTagThrough = Recipe.tags.get_through_model()

models_ = [Recipe, Tag, NutritionInformation, Ingredient, RecipeTagThrough, Recipe_links]


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

from peewee import SqliteDatabase

# Transform Models
from apps.etl_app.etl.extract.ingredient.continente.models import database_proxy as transform_database_proxy


