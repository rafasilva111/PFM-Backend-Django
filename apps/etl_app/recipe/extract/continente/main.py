import json
import logging
import pickle

import requests
import unidecode
from bs4 import BeautifulSoup

from apps.etl_app.recipe.extract.continente.constants import *
from apps.etl_app.recipe.extract.continente.functions import start_recipe_extract_db, persist_recipes_links, \
    separate_unit_title
from apps.etl_app.recipe.extract.continente.models import Recipe, Recipe_links, NutritionInformation, Ingredient, Tag

CONTINENTE_IMAGES_FOLDER = "recipe/extract/continente/images"

BASE_URL = "https://feed.continente.pt"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
}
COMPANY_NAME = "continente"


def extract_data_from_link(recipe_link):
    base_response = requests.get(recipe_link, headers=BASE_HEADERS)
    html = BeautifulSoup(base_response.content, 'html.parser')

    """ General info """

    recipe_db = Recipe()

    " Source Link "
    recipe_db.link = recipe_link

    " Title "
    recipe_db.title = html.find('h1', class_='title font-2xl').text.strip()

    " Company  "
    recipe_db.company = COMPANY_NAME

    " Time, Dificulty, Portions "
    infos = []
    attributes_block = html.find('div', class_='attributesBlock')
    if attributes_block:
        attribute_elements = attributes_block.find_all('div', class_='attribute')

        # Loop through each attribute and extract relevant data
        for attribute_element in attribute_elements:
            if attribute_element.find('i')['title'] != "Custo":
                infos.append(attribute_element.find('strong').text.strip())

    recipe_db.time = infos[0]
    recipe_db.difficulty = infos[1]
    recipe_db.portion = infos[2]

    " Description "

    recipe_db.description = html.find('div', class_='detailsTextBlock').find('p', class_='font-m').get_text(
        separator=' ', strip=True)

    " Rating "

    # impossivel fazer pós a info é carregada após a página ser carregada
    # logo não é possível fazer scraping, apenas com selenium :(

    " Image "

    file_storage = unidecode.unidecode(recipe_db.title).replace(" ", "_")
    image_source_link = Recipe_links.get(Recipe_links.link == recipe_link).image_link
    img_source = f'{CONTINENTE_IMAGES_FOLDER}/{file_storage}.png'
    recipe_db.img = img_source
    try:
        with open(img_source, "wb") as f:
            f.write(requests.get(image_source_link).content)
    except Exception as e:
        print(e)

    " Preparation "

    try:
        # Find the <div> element with the specified class name
        recipe_steps_raw = html.find('div', class_='recipeSteps__body')

        preparation = []
        if recipe_steps_raw:
            list_items = recipe_steps_raw.find_all('li')
            section = "main"
            # Loop through each list item and extract the step information
            for li_element in list_items:
                if li_element.has_attr('class'):
                    section = li_element.text.strip()
                else:
                    preparation.append({"step": li_element.find('span').text.replace(".", "").strip(),
                                        "section": section,
                                        "description": li_element.find('p').text.strip()})

        recipe_db.preparation = pickle.dumps(preparation)
    except Exception as e:
        print(e, logging.ERROR)

    " Nutrition Information "

    nutritional_table_raw = html.find('div', class_='recipeNutricionalTable__table')

    nutrition_helper = {}
    if nutritional_table_raw:
        rows = nutritional_table_raw.find_all('div', class_='recipeNutricionalTable__table__row')

        for row in rows:
            # Find all <p> elements within the row
            item_elements = row.find_all('p', class_='itemValue')

            # Extract and print the nutritional information
            for item_element in item_elements:
                item_title = item_element.find_previous('p', class_='itemTitle').text.strip()
                item_value = item_element.find('strong').text.replace(",", ".").strip()
                nutrition_helper.update({item_title: item_value})

        nutrition_information = NutritionInformation(energia=nutrition_helper['Calorias'],
                                                     energia_perc="0",
                                                     gordura=nutrition_helper['Lípidos'],
                                                     gordura_perc="0",
                                                     gordura_saturada=nutrition_helper['Saturados'],
                                                     gordura_saturada_perc="0",
                                                     hidratos_carbonos=nutrition_helper['Hidratos'],
                                                     hidratos_carbonos_acucares=nutrition_helper['Açúcares'],
                                                     hidratos_carbonos_acucares_perc="0",
                                                     fibra=nutrition_helper['Fibras'],
                                                     fibra_perc="0",
                                                     proteina=nutrition_helper['Proteínas'],
                                                     proteina_perc="0",
                                                     sal=nutrition_helper['Sal'],
                                                     sal_perc="0")
        nutrition_information.save()
        recipe_db.nutrition_information = nutrition_information.id

    else:
        print("No nutritional information found", logging.WARNING)
    recipe_db.save()

    " Ingredients "

    ingredient_list_raw = html.find('div', class_='ingredientList__body')

    if ingredient_list_raw:
        list_items = ingredient_list_raw.find_all('li')

        section = "main"
        for li_element in list_items:
            if li_element.has_attr('class'):
                section = li_element.text.strip()
            else:
                ingredient_text = li_element.text.strip()
                ingredient = Ingredient(text=ingredient_text, section=section)
                ingredient.recipe = recipe_db.id
                ingredient.save()

    " Tags "

    tags_raw = html.find('div', class_='tags')
    if tags_raw:
        tags_tag = tags_raw.find('span', class_='categoryTag')

        if tags_tag:
            tag, created = Tag.get_or_create(title=tags_tag.text.strip())
            tag.save()
            recipe_db.tags.add(tag)

    recipe_db.save()


def pull_continente_recipes(max_recipes=-1):
    print("Starting to pull Recipes")

    total_recipes = Recipe.select().count()
    print(f"Found {total_recipes} recipes on DB...")

    print("")
    counter = 0
    for recipe_link in Recipe_links.select().where(Recipe_links.id > total_recipes):
        if max_recipes != -1 and counter == max_recipes:
            break
        else:
            counter += 1

        print(f"Extracting recipe {counter} from {recipe_link.link}")
        extract_data_from_link(recipe_link.link)

    if counter == 0:
        print("All recipes were imported")


def get_all_recipes_links(max_recipes=-1, continue_mode=False):
    # todo check if all recipes links are on db

    """ Gets all recipes links from Continente"""

    print("Starting to get all recipes links...")
    print()

    " Base data "

    url = "https://feed.continente.pt/umbraco/api/GraphQL/Post"

    headers = BASE_HEADERS
    headers.update({
        "content-type": "application/json",
    }
    )
    page = 1

    " Get data "

    if continue_mode:
        page = Recipe_links.select().count() // 18 + 1

    while True:

        print(f"Added {page * 18} recipe links from page {page}")

        data = {
            "query": """
            query genericRecipesBy(
                $cost: String,
                $difficulty: String,
                $preparationTime: String,
                $specialNeeds: String,
                $geographicalOrigin: String,
                $category: String,
                $cookingType: String,
                $sort: Int,
                $take: Int,
                $skip: Int,
                $showOnlyYammiRecipes: String
            ) {
                genericRecipesBy(
                    cost: $cost,
                    difficulty: $difficulty,
                    preparationTime: $preparationTime,
                    specialNeeds: $specialNeeds,
                    geographicalOrigin: $geographicalOrigin,
                    category: $category,
                    cookingType: $cookingType,
                    sort: $sort,
                    take: $take,
                    skip: $skip,
                    showOnlyYammiRecipes: $showOnlyYammiRecipes
                ) {
                    alias,
                    id,
                    authorOrChef { authorName, image },
                    category,
                    cookingType,
                    pageVertical,
                    geographicalOrigin,
                    contentName,
                    imageOrVideo,
                    image,
                    preparationTime,
                    introduction,
                    numberOfPortions,
                    difficulty,
                    pageUrl
                }
            }
        """,
            "variables": {
                "sort": 0,
                "take": 18,
                "skip": 18 * (page - 1),
            }
        }

        response = requests.post(url, json=data, headers=headers)

        data_json = json.loads(response.content)
        # check if there are more recipes
        if len(data_json['data']['genericRecipesBy']) == 0:
            break

        for item in data_json['data']['genericRecipesBy']:
            persist_recipes_links(BASE_URL + item['pageUrl'], page, url, item['image'])

        if max_recipes != -1 and page * 18 > max_recipes:
            break
        page += 1

    print("Done")


def __extract_continente(max_recipes=-1, continue_mode=True, new_copy=False):
    print(f"Extracting all recipes from continente")
    print()
    # starts the db

    start_recipe_extract_db(new_copy=new_copy)
    print()

    # get all recipes links
    get_all_recipes_links(max_recipes=max_recipes, continue_mode=continue_mode)
    print()

    # pulls recipes from above links
    pull_continente_recipes(max_recipes=max_recipes)
    print()

    print(f"Done")
    print()
