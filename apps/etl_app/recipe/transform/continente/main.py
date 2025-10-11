" Import necessary modules "
from playhouse.shortcuts import model_to_dict
import google.generativeai as genai
import json

" Import custom functions and constants "
from apps.etl_app.functions import start_db, start_sub_db, strip_markdown_json
from apps.etl_app.constants import TRANSFORM_CONTINENTE_RECIPES_DB, eu_reference_intake
from apps.etl_app.recipe.extract.continente.models import database_proxy as database_proxy_E, Recipe as Recipe_E, RecipeLink as RecipeLink_E, NutritionInformation as NutritionInformation_E, Ingredient as Ingredient_E, Tag as Tag_E, UsefulTool as UsefulTool_E
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.recipe.transform.continente.functions import normalize_time, normalize_portion, normalize_quantity

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_E = Recipe_E.tags.get_through_model()
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
extract_models_ = [Recipe_E, RecipeLink_E, NutritionInformation_E, Ingredient_E, Tag_E, UsefulTool_E, recipeTagThrough_E]
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]

" Define the AI prompt for transforming recipes "
input_data = None  # This will be set later with the actual input data
PROMPT_TEMPLATE = """
Act as an expert in parsing and normalizing recipe ingredients to make them suitable for streamlined grocery shopping.

Given the following input JSON object, extract and normalize:
- The quantity as a float in `quantity_normalized`.
- The measurement unit in Portuguese in `units_normalized` (e.g., "unidade", "grama", "ml").
- The mesaurement should also be shortened for example "grama" to "g", "mililitro" to "ml", "unidade" to "unid.".
- If no clear measurement unit is provided, use "q.b.".
- The cleaned and identifiable name of the ingredient in `ingredient_name`.
- If there's "fatias" in ingredient name assume it as units and remove and the name of the ingredient should be the item after "de" or "do" (e.g., "fatias de queijo" should become "queijo").
- Do the same for embala

You should also maintain the original `id` from the input and as int.

## Example Input:
[
  {{
    "id": 22817,
    "quantity_original": "Casca de 1 lima",
    "quantity_tempered": "casca de 1 lima",
    "quantity_normalized": None,
    "units_normalized": None,
    "extra_quantity": None,
    "extra_units": None,
    "ingredient": {{
      "id": 245,
      "name": "Unknown Ingredient"
    }}
  }}
]

## Example Output:
{{
    22817: {{
    "quantity_normalized": 1.0,
    "units_normalized": "unidade",
    "ingredient_name": "lima"
    }}
}}

---

Now, here's the actual input to process:

{input_data}

Only return the JSON output. No explanation.
"""


def transform_recipe(logger, task, recipe):
       
    " Recipe "
    logger.info(f"Transforming Recipe {recipe.id}.")
    
    _time, _time_units = normalize_time(logger, recipe.time)
    _portion_lower_bound, _portion_upper_bound, _portion_units = normalize_portion(logger, recipe.portion)
    
    _source_rating = float(recipe.rating) if recipe.rating else float(0)
    
    _recipe = Recipe_T(
        company=task.company.name,
        title=recipe.title,
        description=recipe.description,
        image=recipe.image,
        video_link=recipe.video_link,
        difficulty=recipe.difficulty,
        time=_time,
        time_units=_time_units,
        portion_lower=_portion_lower_bound,
        portion_upper=_portion_upper_bound,
        portion_units=_portion_units,
        source_rating = _source_rating,
        source_link=recipe.link,
        preparation=recipe.preparation
    )
    
    _recipe.save()
    
    " Tag "
    
    for tag in recipe.tags:
        _tag, created = Tag_T.get_or_create(text = tag.text)
        if created:
            _tag.save()
        _tag.recipe.add(_recipe)
        _tag.save()
    
    " Useful Tool "
    
    for useful_tool in recipe.useful_tools:
        _useful_tool = UsefulTool_T()
        _useful_tool.text = useful_tool.text
        _useful_tool.recipe = _recipe
        _useful_tool.save()
    
    " Nutrition Information "
    if recipe.nutrition_information:
        _energy_perc = round((float(recipe.nutrition_information.energy_kcal) / eu_reference_intake["energy_kcal"]) * 100, 1)
        _carbohydrates_perc = round((float(recipe.nutrition_information.carbohydrates_g) / eu_reference_intake["carbohydrates_g"]) * 100, 1)
        _salt_perc = round((float(recipe.nutrition_information.salt_g) / eu_reference_intake["salt_g"]) * 100, 1)
        _sugar_perc = round((float(recipe.nutrition_information.sugars_g) / eu_reference_intake["sugars_g"]) * 100, 1)
        _fat_perc = round((float(recipe.nutrition_information.fat_g) / eu_reference_intake["fat_g"]) * 100, 1)
        _saturates_perc = round((float(recipe.nutrition_information.saturates_g) / eu_reference_intake["saturates_g"]) * 100, 1)
        _protein_perc = round((float(recipe.nutrition_information.protein_g) / eu_reference_intake["protein_g"]) * 100, 1)
        
        _nutrition_information = NutritionInformation_T(
            energy_kcal = recipe.nutrition_information.energy_kcal,
            energy_perc = _energy_perc,
            carbohydrates_g = recipe.nutrition_information.carbohydrates_g,
            carbohydrates_perc = _carbohydrates_perc,
            sugars_g = recipe.nutrition_information.sugars_g,
            sugars_perc = _sugar_perc,
            fat_g = recipe.nutrition_information.fat_g,
            fat_perc = _fat_perc,
            saturates_g = recipe.nutrition_information.saturates_g,
            saturates_perc = _saturates_perc,
            protein_g = recipe.nutrition_information.protein_g,
            protein_perc = _protein_perc,
            salt_g = recipe.nutrition_information.salt_g,
            salt_perc = _salt_perc,
            fiber_g = recipe.nutrition_information.fiber_g
        )
        _nutrition_information.save()
    
        _recipe.nutrition_information = _nutrition_information
        _recipe.save()   
    
    " Ingredient "
    for ingredient in recipe.ingredients:
        
        
        _ingredient_quantity = IngredientQuantity_T()
        _ingredient_quantity.quantity_original = ingredient.text
        _ingredient_quantity.quantity_tempered,_ingredient_quantity.units_normalized,_ingredient_quantity.quantity_normalized,\
        _ingredient_quantity.extra_quantity,_ingredient_quantity.extra_units, _ingredient = normalize_quantity(logger, task, ingredient.text)
        _ingredient_quantity.recipe = _recipe
        
        
        if _ingredient == None:
            task.increment_warnings(
                logger = logger,
                message = f"Transformation of Ingredient Quantity ( {_ingredient_quantity.quantity_original} ) lead to a None Ingredient."
            )
            _recipe.valid = False
            _recipe.save() 
            _ingredient = "Unknown Ingredient"
        
        _ingredient, created = Ingredient_T.get_or_create(name = _ingredient)
        
        _ingredient_quantity.ingredient = _ingredient
        _ingredient_quantity.save()
        
    task.items_processed += 1
    
    return task
    
    
def transform_recipes(logger, task, resume):
    
    " Initialize the control variables "
    OFFSET = None
    
    " Log the start of the transform process "
    logger.info("")
    logger.info("Starting to transform Recipes...")
    logger.info("")

    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.owner_job and task.owner_job.stopping_condition and isinstance(task.owner_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if resume:
        logger.info(f"Resuming Recipe Transformation on step {task.step}...")
        logger.info("")
        recipes_in_db = Recipe_T.select().count()
        if recipes_in_db > task.step:
            # Delete tasks until step matches recipes_in_db
            tasks_to_delete = Recipe_T.select().order_by(Recipe_T.id.desc())
            for t in tasks_to_delete:
                if task.step == recipes_in_db:
                    break
                t.tags.clear()
                t.delete_instance()
                recipes_in_db -= 1
    else:
        logger.info("Starting Recipe Transformation...")
        logger.info("")
    
    " Transform data from each Extracted recipe "
    for recipe in Recipe_E.select().where(Recipe_E.id > task.step):
        
        if OFFSET and recipe.id > OFFSET:
            task.owner_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                action=JobTriggerHistory.Action.REST,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {recipe.id}...")
            logger.info("")
            return task, False # Task was not fully completed (False)
        
        task = transform_recipe(logger, task, recipe)
        task.step += 1
        task.save()

    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes transformed ...")
    logger.info("")
    
    return task, True # Task was fully completed (True)

def tansform_recipes_ai(logger, task):
    
    logger.info("Starting AI Transformation of invalid Recipes...")
    ingredient_dicts = []
    for recipe in Recipe_T.select().where(Recipe_T.valid == False):
        recipe.valid = True
        recipe.save()
        for ingredient in recipe.ingredients:
            if not ingredient.quantity_normalized and not ingredient.units_normalized:
                # Mark the ingredient for AI
                ingredient.ai = True
                ingredient.save()
                
                ingredient_dict = model_to_dict(ingredient, backrefs=True, recurse=True, exclude=[IngredientQuantity_T.recipe])
                ingredient_dicts.append(ingredient_dict)
                
    if not ingredient_dicts:
        logger.info("No invalid recipes found for AI transformation.")
        logger.info("")
        return task
    
    ingredients_json = json.dumps(ingredient_dicts, ensure_ascii=False, indent=4)
   
    # Configure API Key
    genai.configure(api_key="")

    # Create the model
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # Prompt string
    prompt = PROMPT_TEMPLATE.format(input_data=ingredients_json)
    
    # Make the request
    response = model.generate_content(prompt)
    
    # Parse the response
    clean = strip_markdown_json(response.text)
    result = json.loads(clean)
    
    for key, value in result.items():
        
        ingredient_quantity = IngredientQuantity_T.get_or_none(int(key))
        ingredient_quantity.ai = True
        
        if not ingredient_quantity:
            logger.warning(f"Ingredient Quantity with ID {key} not found in the database.")
            continue
        
        ingredient_quantity.quantity_normalized = value.get("quantity_normalized")
        ingredient_quantity.units_normalized = value.get("units_normalized")
        ingredient, created = Ingredient_T.get_or_create(name = value.get("ingredient_name"))
        ingredient_quantity.ingredient = ingredient
        ingredient_quantity.save()
        
    logger.info("")
    
    return task

def __transform_continente_recipes(logger, task, resume):
    
    " Log the start of the transform process "
    logger.info(f"Initializing the {task.type} of recipes from {task.company.name}...")
           
    " Start the Transform database "
    logger.info("Initializing Transform database ...")
    task, database = start_db(
        logger=logger,
        task=task,
        models=transform_models_,
        path=TRANSFORM_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset= False #not resume # we want to reset the database if we are not resuming
    )
    

    " Starts the Extract database "
    logger.info("Initializing Extract database ...")
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=extract_models_,
        database_proxy=database_proxy_E
    )
    logger.info("")
    
    
    " Calculate the number of recipes expected to be loaded "
    task.items_expected = Recipe_E.select().count()
    task.save()
    
    " Transform Elements "
    task, completed = transform_recipes(logger, task, resume)

    " Try to transform using AI"
    #task = tansform_recipes_ai(logger, task)
    
    " Log the completion of the Transformation process "
    logger.info("Summary:")
    logger.info(f"Recipes Expected: {task.items_expected}")
    logger.info(f"Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    if completed:
        task.finish(kill_celery_task=False)
    else:
        task.pause()
    
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info(f"> Done...")
    logger.info("")
    
    return task