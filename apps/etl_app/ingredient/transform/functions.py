import pickle
from peewee import SqliteDatabase
from apps.etl_app.constants import transform_recipe
from apps.etl_app.recipe.transform.transformation_functions import remove_special_characters,remove_fraction_characters,\
transform_unids,transform_embs,transform_soup_spoon,transform_tea_spoon,transform_desert_spoon,transform_coffe_spoon,transform_number
import re
from django.db import models

class Weight_Units(models.TextChoices):
    GRAMS = 'g','Gramas'
    UNITS = 'U','Unidades'
    DENTES = 'D','Dentes'
    FOLHA = 'F','Folhas'
    MILILITROS = 'ml','Mililitros'
    LITROS = 'l','Litros'
    QB = 'QB'

# Transform Models
from apps.etl_app.recipe.transform.models import Recipe, NutritionInformation,IngredientQuantity, Tag, Ingredient, Preparation,database_proxy as transform_database_proxy

# Extract Models
from apps.etl_app.recipe.extract.pingo_doce.models import Recipe as Recipe_, Tag as Tag_, NutritionInformation as NutritionInformation_, Ingredient as Ingredient_, \
    Recipe_links as Recipe_links_,IngredientQuantity as IngredientQuantity_,database_proxy as extract_database_proxy
    


RecipeTagThrough = Recipe.tags.get_through_model()

models_ = [Recipe,Preparation, NutritionInformation,IngredientQuantity, RecipeTagThrough,Tag, Ingredient]

def start_recipe_transform_db(logger, task, reset=False):
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
    logger.info("Starting Recipe Transform Database...")
    
    # Save the task with the new sql file name
    task_sql_file = f"{transform_recipe}/db_{task.id}.sql"
    

    from apps.etl_app.models import TaskType
    
    if task.type == TaskType.FULL_PROCESS:
        task.transform_sql_file = task_sql_file
    else:
        task.sql_file = task_sql_file

    task.save()

    # Create a new database instance
    transform_recipes_db = SqliteDatabase(task_sql_file)    
    
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    transform_database_proxy.initialize(transform_recipes_db)
    
    # Connect to the database
    transform_recipes_db.connect()
    
    # If reset is True, drop all tables in the database
    if reset:
        logger.info("Reseting Database...")
        transform_recipes_db.drop_tables(models_)
    
    # Create all tables in the database
    transform_recipes_db.create_tables(models_)
    
    # Return the new database instance
    return transform_recipes_db


def start_recipe_extract_db(logger, task):

    
    # Log the start of the recipe extract database
    logger.info("Starting Recipe Extract Database...")
   

    from apps.etl_app.models import TaskType
    
    if task.type == TaskType.FULL_PROCESS:
        task_sql_file = task.extract_sql_file 
    else:
        task_sql_file = task.sql_file 
        
    # Create a new database instance
    extract_recipes_db = SqliteDatabase(task_sql_file)    
    
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    extract_database_proxy.initialize(extract_recipes_db)
    
    # Connect to the database
    extract_recipes_db.connect()
    
    # Return the new database instance
    return extract_recipes_db


def verify_data_integrity(logger):

    # Log the start of the recipe extract database
    logger.info("Verifying data integrity...")
    
    for recipe in Recipe.select():
         
        ##
        #   1 - Verify quantity
        ##

        for ingredient in recipe.ingredients:

            # Verify quantity original
            if not ingredient.quantity_original:
                recipe.is_valid = False
                recipe.save()
                break
            
            # Verify quantity original
            if not ingredient.quantity_normalized and not ingredient.extra_quantity:
                recipe.is_valid = False
                recipe.save()
                break
    

         

        



def json_to_recipe_model(recipe_transformed):
    """ Removing information from recipe_transformed """

    preparation_information = recipe_transformed.pop('preparation')
    nutrition_information = recipe_transformed.pop('nutrition_information')
    ingredients_information = recipe_transformed.pop('ingredients')
    tags_information = recipe_transformed.pop('tags')

    """ Creating recipe_model """

    recipe_model = Recipe(**recipe_transformed)

    """ Inserting information into recipe_model """

    

    " Nutrition information "
    if nutrition_information:
        nutrition_information_model = NutritionInformation.create(**nutrition_information)
        recipe_model.nutrition_information = nutrition_information_model.id

    # we need to save the recipe_model before we can add tags and ingredients has it is a manytomanyfield
    recipe_model.save()

    " Preparation "
    for item in preparation_information:
        preparation = Preparation(**item)
        preparation.recipe = recipe_model.id
        preparation.save()


    " Ingredients "
    for item in ingredients_information.copy():
        ingredient = item.pop('ingredient')
        ingredient_model, created = Ingredient.get_or_create(**ingredient)
        if created:
            ingredient_model.save()

        ingredient_quantity_model = IngredientQuantity(**item)
        ingredient_quantity_model.ingredient = ingredient_model.id
        ingredient_quantity_model.recipe = recipe_model.id
        ingredient_quantity_model.save()

    " Tags "
    for tag in tags_information:
        tag, created = Tag.get_or_create(**tag)
        if created:
            tag.save()
        recipe_model.tags.add(tag)

    recipe_model.save()


COLHER_DE_CHA = 4
COLHER_DE_SOPA = 14
COLHER_DE_SOBREMESA = 9
COLHER_DE_CAFE = 1.5
CHAVENA = 250

def normalize_quantity(logger,quantity_original):
    """
    Normalize the given quantity string by performing string sanitation and pattern matching.

    Args:
        logger (object): logger object for logging errors.
        quantity_original (str): the original quantity string to be normalized.

    Returns:
        tuple: a tuple containing the normalized quantity string, units, value, extra units, and extra value.
               If no transformation is possible, returns the original quantity string, None for units, value, extra units, and extra value.

    Raises:
        Exception: if an error occurs during the transformation process.
    """
    
    units = None
    value = None
    extra_units = None
    extra_value = None
    
    
    ##
    #   1 - String Sanitation
    #   
    ##
    
    # Remove spaces
    
    quantity_original = quantity_original.strip()
    
    # Swap commas by dots
    
    quantity_original = quantity_original.replace(",", ".")
    
    # Remove (±) , ± , +-
    
    quantity_original = remove_special_characters(quantity_original)
    
    # Remove fractions ½ , 1⁄2 , ¼
    
    quantity_original = remove_fraction_characters(quantity_original)
    
    
    
    
    
    ##
    #   2 - Patterns
    #
    ##

    # checked
    try:
        """
        Search for patterns strings containing "unid."
        """
        if "uni" in quantity_original:
            return transform_unids(logger,quantity_original)
    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
            
    
    # checked
    try:
        """
        Search for patterns strings containing "emb"
        """
        if "emb" in quantity_original:
            return transform_embs(logger,quantity_original)

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
    
    
    # checked
    try:
        """
        Search for patterns strings containing "c. de sopa"
        """
        if "c. de sopa" in quantity_original:
            quantity_original, units, value, extra_units, extra_value, extra_plus = transform_soup_spoon(logger,quantity_original)

            if not extra_plus:
                return quantity_original, units, value,extra_value, extra_units

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
    
    
    # checked
    try:
        """
        Search for patterns strings containing "c. de chá"
        """
        if "c. de chá" in quantity_original:
            quantity_original, units, value, extra_units, extra_value, extra_plus = transform_tea_spoon(logger,quantity_original)

            if not extra_plus:
                return quantity_original, units, value,extra_value, extra_units

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
    
    
    # checked
    try:
        """
        Search for patterns strings containing "c. de sobremesa"
        """
        if "c. de sobremesa" in quantity_original:
            quantity_original, units, value, extra_units, extra_value, extra_plus = transform_desert_spoon(logger,quantity_original)

            if not extra_plus:
                return quantity_original, units, value,extra_value, extra_units

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None


    """
    Search for patterns strings containing "c. de café"
    and call `transform_coffe_spoon` function.

    Args:
        logger (object): logger object
        quantity_original (str): quantity string

    Returns:
        tuple: quantity_original, units, value, extra_units, extra_value, extra_plus

    Raises:
        Exception: if there's an error while trying to transform the quantity string
    """
    try:
        if "c. de café" in quantity_original:
            quantity_original, units, value, extra_units, extra_value, extra_plus = transform_coffe_spoon(logger,quantity_original)

            if not extra_plus:
                return quantity_original, units, value,extra_value, extra_units

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
    

    
    """
    Search for patterns strings containing a number and a unit (e.g., "2 g") and
    return the quantity_original, units, and value.

    Args:
        logger (object): logger object
        quantity_original (str): input quantity to normalize

    Returns:
        tuple: quantity_original, units, value, None, None

    Raises:
        Exception: if there is an error while trying to transform the quantity_original
    """
    try:


        quantity_original, units, value  = transform_number(logger,quantity_original)

        if units and value:
            return quantity_original, units, value, None, None

    except Exception as e:
            logger.error(f"Error happened while trying to transform: {quantity_original}")
            logger.error(e)
            return quantity_original, None, None, None, None
    
   

    return quantity_original, None, None, None, None


def remove_non_numeric(input_string):
    return re.sub(r'\D', '', input_string)