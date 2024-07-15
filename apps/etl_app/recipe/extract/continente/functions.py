import logging
import re

from apps.etl_app.constants import extract_recipe_continente_db, extract_recipe_continente
from apps.etl_app.functions import print_it
from apps.etl_app.recipe.extract.continente.models import Recipe, Tag, NutritionInformation, Ingredient, \
    Recipe_links

RecipeTagThrough = Recipe.tags.get_through_model()

models_ = [Recipe, Tag, NutritionInformation, Ingredient, RecipeTagThrough, Recipe_links]


def start_recipe_extract_db(new_copy=False):
    print_it("Starting Recipe Extract Database...")

    if new_copy:
        # Save old db
        print_it("Starting a new copy of the database...")
        save_sql_file(extract_recipe_continente)

    extract_recipe_continente_db.connect()
    # db.drop_tables(models)
    extract_recipe_continente_db.create_tables(models_)


def persist_recipes_links(link, page, base_search_link, image_link):
    if link != "https://feed.continente.pt":
        data_point = Recipe_links(link=link, page=page, base_search_link=base_search_link, image_link=image_link)
        data_point.save()

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

