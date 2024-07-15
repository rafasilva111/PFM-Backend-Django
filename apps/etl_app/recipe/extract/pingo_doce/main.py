import json
import pickle
from django.utils import timezone
import requests
import unidecode as unidecode
from bs4 import BeautifulSoup
from peewee import fn
from os import path
#from apps.etl_app.models import bcolors
from apps.etl_app.constants import PINGO_DOCE_IMAGES_FOLDER
from apps.etl_app.recipe.extract.pingo_doce.functions import start_recipe_extract_db
from apps.etl_app.recipe.extract.pingo_doce.models import Tag, Recipe, NutritionInformation, \
    Ingredient, Recipe_links, IngredientQuantity


PINGO_DOCE_BASE_URL = "https://www.pingodoce.pt/receitas/pesquisa/"
PINGO_DOCE_SEARCH_ALL_URL = "https://www.pingodoce.pt/wp-content/themes/pingodoce/ajax/pd-ajax.php?action=pd_recipe_load_more&c=Search&q=cT0mbz1kYXRhJmM9cmVjaXBl&p="

COMPANY_NAME = "pingo_doce"


def persist_recipes_links(link, page, base_search_link, image_link):
    data_point = Recipe_links(link=link, page=page, base_search_link=base_search_link, image_link=image_link)
    data_point.save()


def extract_data_from_link(logger,recipe_link):
    base_response = requests.get(recipe_link)
    html = BeautifulSoup(base_response.content, 'html.parser')
    title = html.find("title").text.split("|")[0].strip()
    company = COMPANY_NAME
    infos = [[a.text, a.find("img", alt=True)['alt']] for a in html.find('div', class_="short-info").find_all('div')]

    ingredients_raw = [a for a in html.find_all('div', class_="ingredient")]

    ingredients = {}
    first_title = None
    first_ingredients = []
    for item in ingredients_raw:
        teste = item.attrs['class']
        if teste[1] == 'title':
            if not first_title:
                first_title = item.text.strip()
            else:
                ingredients[first_title] = first_ingredients
                first_ingredients = []
                first_title = item.text.strip()
        if teste[1] == 'ingredient':
            first_ingredients.append(item.text.strip())
    ingredients[first_title] = first_ingredients

    preparation_raw = [a.text for a in html.find_all('div', class_="step-description")]

    desc = html.find("div", class_="intro-text").text

    tags = [a['href'].split('/')[3].capitalize() for a in html.find_all('a', class_="tag")]

    badges = html.find('div', class_="badges")
    if badges:
        [tags.append(a['alt']) for a in html.find('div', class_="badges").find_all('img', alt=True)]

    try:
        tabela_nutricional = [a.text.strip() for a in
                              html.find('table', class_="table js-nutritional-table").find_all('tr')]
    except Exception as e:
        tabela_nutricional = None
        logger.info("No nutritional table")

    tempo_raw = ""
    dificuldade_raw = "Fácil"
    portion_raw = ""
    rating_raw = ""
    for item in infos:
        if "tempo" in item[1].lower():
            tempo_raw = item[0]
        elif "dificuldade" in item[1].lower():
            dificuldade_raw = item[0]
        elif "pessoas" in item[1].lower():
            portion_raw = item[0]
        elif "estrela" in item[1].lower():
            rating_raw = item[0]
    string_helper = title.replace(chr(34), '').replace(" ", "_").replace('“', '').replace('”', '')

    # image

    file_storage = unidecode.unidecode(string_helper)
    image_source_link = Recipe_links.get(Recipe_links.link == recipe_link).image_link
    img_source = f'{PINGO_DOCE_IMAGES_FOLDER}/{file_storage}.png'
    if not path.exists(img_source):
        try:
            with open(img_source, "wb") as f:
                f.write(requests.get(image_source_link).content)
        except Exception as e:
            logger.error(f"Error downloading image from {image_source_link}: {e}")

    # fills recipe object
    recipe_db = Recipe(title=title, source=recipe_link, company=company,
                       img_source=img_source,
                       time=tempo_raw, difficulty=dificuldade_raw, source_rating=rating_raw, source_link=recipe_link,
                       portion=portion_raw, description=desc)

    preparation = []
    counter = 1
    section = "main"
    for value in preparation_raw:
        preparation.append({"step": counter,"section": section, "description": value})
        counter += 1

    recipe_db.preparation = pickle.dumps(preparation)

    # nutritional_information

    try:
        if tabela_nutricional and tabela_nutricional != {}:
            tabela_nutricional.pop(0)
            energia = ""
            energia_perc = ""
            gordura = ""
            gordura_perc = ""
            gordura_saturada = ""
            gordura_saturada_perc = ""
            hidratos_carbono = ""
            hidratos_carbonos_acucares = ""
            hidratos_carbonos_acucares_perc = ""
            fibras = ""
            fibras_perc = ""
            proteina = ""
            for item in tabela_nutricional:
                result = item.split("\n")
                len_result = len(result)
                if "energia" in result[0].lower():
                    if len_result == 2:
                        energia_perc = ""
                    else:
                        energia_perc = result[2]
                    energia = result[1]
                    continue

                if "gordura" in result[0].lower():
                    if len_result == 2:
                        gordura_perc = ""
                    else:
                        gordura_perc = result[2]
                    gordura = result[1]
                    continue

                if "das quais saturadas" in result[0].lower():
                    if len_result == 2:
                        gordura_saturada_perc = ""
                    else:
                        gordura_saturada_perc = result[2]
                    gordura_saturada = result[1]
                    continue

                if "das quais saturadas" in result[0].lower():
                    if len_result == 2:
                        gordura_saturada_perc = ""
                    else:
                        gordura_saturada_perc = result[2]
                    gordura_saturada = result[1]
                    continue

                if "hidratos de" in result[0].lower():
                    hidratos_carbono = result[1]
                    continue

                if "dos quais" in result[0].lower():
                    if len_result == 2:
                        hidratos_carbonos_acucares_perc = ""
                    else:
                        hidratos_carbonos_acucares_perc = result[2]
                    hidratos_carbonos_acucares = result[1]
                    continue

                if "fibra" in result[0].lower():
                    if len_result == 2:
                        fibras_perc = ""
                    else:
                        fibras_perc = result[2]
                    fibras = result[1]
                    continue

                if "prote" in result[0].lower():
                    proteina = result[1]
                    continue

            nutrition_information = NutritionInformation(energia=energia,
                                                         energia_perc=energia_perc,
                                                         gordura=gordura,
                                                         gordura_perc=gordura_perc,
                                                         gordura_saturada=gordura_saturada,
                                                         gordura_saturada_perc=gordura_saturada_perc,
                                                         hidratos_carbonos=hidratos_carbono,
                                                         hidratos_carbonos_acucares=hidratos_carbonos_acucares,
                                                         hidratos_carbonos_acucares_perc=hidratos_carbonos_acucares_perc,
                                                         fibra=fibras,
                                                         fibra_perc=fibras_perc,
                                                         proteina=proteina)

            nutrition_information.save()
            recipe_db.nutrition_information = nutrition_information.id

    except Exception as e:
        logger.error(e)
        return

    recipe_db.save()
    ## recipe needs to be saved after foreign key's but before multiple to multiple relations
    # because to build these last one recipe needs to already have an id, wich is done by save()

    # ingredients

    try:
        if first_ingredients and first_ingredients != {}:
            for item in first_ingredients:
                helper = item.split("\n")
                ingredient, created = Ingredient.get_or_create(name=helper[0])
                if created:
                    ingredient.save()

                if len(helper) == 1:
                    ingredient_quantity = IngredientQuantity(quantity_original="")
                else:
                    ingredient_quantity = IngredientQuantity(quantity_original=helper[1])
                ingredient_quantity.ingredient = ingredient
                ingredient_quantity.recipe = recipe_db
                ingredient_quantity.save()
    except Exception as e:
        recipe_db.delete_instance(recursive=True)
        print("Something happened to ingredients")
        logger.error(e)
        return

    # tags

    try:
        if tags and tags != []:
            for t in tags:
                tag, created = Tag.get_or_create(title=t)
                tag.save()
                recipe_db.tags.add(tag)

    except Exception as e:
        recipe_db.delete_instance(recursive=True)
        logger.error("Something happened to tags")
        logger.error(e)
        return

    # finally build full object

    recipe_db.save()
    logger.info(f"Added new recipe whit ID: {recipe_db.id}")


def pull_pingo_doce_recipes(logger,task):

    total_recipes = Recipe.select().count()
    logger.info(f"Found {total_recipes} recipes on DB")

    logger.info("")
    counter = total_recipes
    for recipe_link in Recipe_links.select().where(Recipe_links.id > total_recipes):
        
        if counter == 10:
            print()

        if  counter == task.max_records:
            break
        
        extract_data_from_link(logger,recipe_link.link)
        counter += 1
        
    logger.info("")
    logger.info("All recipes were imported")


def pull_pingo_doce_recipes_by_id(id):
    print_it("Starting to pull Recipes...")

    extract_data_from_link(Recipe_links.get(Recipe_links.id == id).link)


def check_if_all_recipes_links_on_db(logger):
    base_response = requests.get(PINGO_DOCE_SEARCH_ALL_URL + str(1))
    site_json = json.loads(base_response.content)
    nr_results_site = int(site_json['data']['total'])
    nr_results_db =  Recipe_links.select(fn.COUNT(Recipe_links.id)).scalar()
    
    if nr_results_site != nr_results_db:
            return False,nr_results_db
    else:
        logger.info("All recipes links were imported")
        return True,nr_results_db


def check_if_all_recipes_on_db():
    base_response = requests.get(PINGO_DOCE_SEARCH_ALL_URL + str(1))
    site_json = json.loads(base_response.content)
    nr_results = site_json['data']['total']
    try:
        if int(nr_results) != Recipe.select().order_by(Recipe.id.desc()).get().id:
            return False
        else:
            print_it("All recipes were imported")
            return True

    except Exception as e:
        pass

    return False


def get_all_recipes_links(logger,task):

    """ Checks if all recipe links are in database """

    all_in_db,nr_results_db = check_if_all_recipes_links_on_db(logger)
    max_records = task.max_records if task.max_records else float('inf') # infinite positive
    
    if all_in_db:
        return
    
    if nr_results_db >= max_records:
        return

    

    logger.info(f"Found {nr_results_db} recipe links on DB")

    """ Gets all recipes links from pingo doce """

    nr_results = None
    try:
        
        ##falta melhorar isto verificar que as paginas não ficaram a meio
        ##sinceramente não é necessario mas ficava com a logica certinha
        page_number = int(Recipe_links.select().order_by(Recipe_links.id.desc()).get().page) + 1
    except Exception as e:
        page_number = 1

    logger.info("")
    while nr_results_db < max_records:

        logger.info(f"Added {page_number * 24} recipe links from page {page_number}")
        base_search_link = PINGO_DOCE_SEARCH_ALL_URL + str(page_number)
        base_response = requests.get(base_search_link)
        site_json = json.loads(base_response.content)

        if not nr_results:
            nr_results = site_json['data']['total']
        results = str(site_json['data']['html'])
        html = BeautifulSoup(results, 'html.parser')
        links = [a['href'] for a in html.find_all('a')]
        image_link = [a['src'] for a in html.find_all("img")]

        for x in range(0, 24):
            try:
                persist_recipes_links(links[x], page_number, base_search_link, image_link[x])
            except:
                logger.info("All imported")
                return
        nr_results_db += 24
        page_number += 1


def __extract_pingo_doce(logger, task):
    """
    Extracts all recipes from pingo_doce.

    Args:
        logger (Logger): Logger object for logging messages.
        task (Task): Task object containing task details.

    Returns:
        None
    """
    
    # Log the start of the extraction process
    logger.info(f"Extracting all recipes from pingo_doce...")
    logger.info("")
    
    # Start the recipe extract database
    start_recipe_extract_db(logger,task)
    logger.info("")
    
    # Get all recipes links
    logger.info("Getting all recipes links...")
    get_all_recipes_links(logger,task)  # If not a new copy, it will continue
    logger.info("")
    
    
    # Pull recipes from above links
    logger.info("Pulling recipes from links...")
    pull_pingo_doce_recipes(logger,task)
    logger.info("")

    # Finish task
    task.finished_at = timezone.now()
    task.status = task.Status.FINISHED
    task.save()
    
    # Log the completion of the extraction process
    logger.info(f"Done...")
    logger.info("")
