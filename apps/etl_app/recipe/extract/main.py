from classes import bcolors
from functions import print_it
from ingredient.extract.continente.main import __extract_ingredients_continente
from recipe.extract.continente.main import __extract_continente
from recipe.extract.pingo_doce.main import __extract_pingo_doce


def _extract_recipes(pingo_doce=True, continente=True, new_copy=True):
    """
            Extract
            :param pingo_doce: if True, it will extract all recipes from pingo doce
            :param continente: if True, it will extract all recipes from continente
            :param new_copy: if True, it will create a new copy of the database, saving the old one
    """

    print_it(f"Extracting all recipes...")
    print_it()
    print_it()
    if pingo_doce:
        __extract_pingo_doce(max_recipes=-1, continue_mode=True, new_copy=new_copy)

    if continente:
        __extract_continente(max_recipes=5000, continue_mode=True, new_copy=new_copy)


def _extract_ingredients(continente=True, new_copy=False):
    """
            Extractce
            :param continente: if True, it will extract all recipes from continente
            :param new_copy: if True, it will create a new copy of the database, saving the old one
    """

    print_it(f"Extracting all ingredients...")
    print_it()
    print_it()

    if continente:
        __extract_ingredients_continente(max_ingredients=-1, continue_mode=True, new_copy=new_copy)


def _extract_all(extract_ingredients=True, extract_recipes=True, pingo_doce=True, continente=True, new_copy=False):
    """
        Extract all
        :param extract_ingredients: if True, it will extract all ingredients
        :param extract_recipes:  if True, it will extract all recipes
        :param pingo_doce: if True, it will extract all recipes from pingo doce
        :param continente: if True, it will extract all recipes from continente
        :param new_copy: if True, it will create a new copy of the database, saving the old one
        :return:
    """

    print_it(f"Starting Extraction Process ...")
    print_it()
    print_it()

    if extract_recipes:
        _extract_recipes(pingo_doce=pingo_doce, continente=continente, new_copy=new_copy)

    if extract_ingredients:
        _extract_ingredients(continente=continente, new_copy=new_copy)


