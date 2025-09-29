" Import necessary modules "
from playhouse.shortcuts import model_to_dict
import pickle
import traceback

" Import custom functions and constants "
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET, COMPANY_CONTINENTE
from apps.common.functions import send_image_to_firebase, lower_and_underscore
from apps.recipe_app.serializers import RecipeSerializer
from apps.recipe_app.models import RecipeAuditLog, Recipe, Tag, UsefulTool, Preparation, Ingredient, IngredientQuantity, NutritionInformation
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]


def load_recipe(logger, task, recipe):
    
    
    " Recipe "
    
    logger.info(f"Loading Recipe {recipe}.")
    
    recipe_t = model_to_dict(recipe, backrefs=True, recurse=True)
    #https://feed.continente.pt/receitas/yammi/granizado-limao-hortela-xl
    __recipe, created = Recipe.objects.get_or_create(
        created_by=task.company.user_account,
        source_link=recipe.source_link
    )
    
    if created:
        logger.info(f"Recipe is new, creating in Main database.")
        persist_recipe(logger, task, __recipe, recipe_t)
        
    else:
        logger.info(f"Recipe already exists in Main database.")
        
        audit_logs_count = RecipeAuditLog.objects.filter(recipe=__recipe).count()
        
        if audit_logs_count >= 1:
            logger.info(f"Found {audit_logs_count} Audit Logs for Recipe.")
        else:
            logger.info(f"Not found any Audit Logs for Recipe.")
        
        
        logger.info(f"Checking for changes in Recipe ...")
        
        mapped_fields = {}

        recipe_t.pop('id')
        recipe_t.pop('company')
        recipe_t.pop('created_date')
        recipe_t.pop('updated_date')
        
        _nutrition_information = recipe_t.pop('nutrition_information')
        _preparation = pickle.loads(recipe_t.pop('preparation'))
        _ingredients_quantity = recipe_t.pop('ingredients')
        _useful_tools = recipe_t.pop('useful_tools')
        _tag_recipe_through = recipe_t.pop('tagrecipethrough_set')
        
        recipe_t['image'] = f"{FIREBASE_STORAGE_COMPANY_BUCKET}{lower_and_underscore(COMPANY_CONTINENTE)}/recipes/{recipe_t['image'].split('/')[-1]}"
        
        " Check for changes in Recipe fields "
        for field in recipe_t.keys():
            
            if hasattr(Recipe, field):
                peewee_value = recipe_t[field]
                django_value = getattr(__recipe, field)
        
                if peewee_value != django_value:
                    mapped_fields[field] = {"old": django_value, "new": peewee_value}
                    setattr(__recipe, field, peewee_value)
                    __recipe.save()
                    
            else:
                # Log an error if the field does not exist in the Django Recipe model
                task.increment_errors(
                    logger = logger,
                    message = f"Field {field} does not exist in Django Recipe model."
                )
        
        
        " Check for changes in Preparation "
        mapped_fields['preparation'] = []

        # Create a dictionary for existing preparation steps for quick lookup
        existing_preparation_dict = {prep.step: prep for prep in __recipe.preparation.all()}
        incoming_preparation_dict = {item['step']: item for item in _preparation}

        # Identify and delete removed preparation steps
        for step, prep_obj in existing_preparation_dict.items():
            if step not in incoming_preparation_dict:
                mapped_fields['preparation'].append({
                    "deleted": {
                        "id": prep_obj.id,
                        "step": step
                    }
                })
                prep_obj.delete()

        # Process incoming preparation steps
        for step, item in incoming_preparation_dict.items():
            if step in existing_preparation_dict:
                # Update existing preparation step
                prep_obj = existing_preparation_dict[step]
                for field, peewee_value in item.items():
                    if field == 'id':
                        continue  # Skip the 'id' field
                    if hasattr(Preparation, field):
                        django_value = getattr(prep_obj, field, None)
                        if peewee_value != django_value:
                            mapped_fields['preparation'].append({
                                "updated": {
                                    "field": field,
                                    "old": django_value,
                                    "new": peewee_value
                                }
                            })
                            setattr(prep_obj, field, peewee_value)
                            prep_obj.save()
                    else:
                        task.increment_errors(
                            logger = logger,
                            message = f"Field {field} does not exist in Django Preparation model."
                        )
            else:
                # Create new preparation step
                new_prep = Preparation.objects.create(
                    recipe=__recipe,
                    step=item['step'],
                    description=item.get('description', '')
                )
                mapped_fields['preparation'].append({
                    "created": {
                        "step": item['step'],
                        "description": item.get('description', '')
                    }
                })
                    
        
        " Check for changes in Ingredients "
        mapped_fields['ingredients_quantity'] = []

        # Create dictionaries for quick lookup of existing and incoming ingredients
        existing_ingredients_dict = {ingredient.ingredient.name: ingredient for ingredient in __recipe.ingredients.all()}
        incoming_ingredients_dict = {item['ingredient']['name']: item for item in _ingredients_quantity}

        # Identify and delete removed ingredients
        for ingredient_name, ingredient_obj in existing_ingredients_dict.items():
            if ingredient_name not in incoming_ingredients_dict:
                mapped_fields['ingredients_quantity'].append({
                    "deleted": {
                        "id": ingredient_obj.id,
                        "ingredient": ingredient_name,
                        "quantity_original": ingredient_obj.quantity_original,
                        "quantity_normalized": ingredient_obj.quantity_normalized,
                        "units_normalized": ingredient_obj.units_normalized,
                        "extra_quantity": ingredient_obj.extra_quantity,
                        "extra_units": ingredient_obj.extra_units
                    }
                })
                ingredient_obj.delete()

        # Process incoming ingredients
        for ingredient_name, item in incoming_ingredients_dict.items():
            if ingredient_name in existing_ingredients_dict:
                # Update existing ingredient quantities and check for changes
                ingredient_obj = existing_ingredients_dict[ingredient_name]
                for field in ['quantity_original', 'quantity_normalized', 'units_normalized', 'extra_quantity', 'extra_units']:
                    if hasattr(IngredientQuantity, field):
                        peewee_value = item.get(field)
                        django_value = getattr(ingredient_obj, field, None)
                        if peewee_value != django_value:
                            mapped_fields['ingredients_quantity'].append({
                                "updated": {
                                    "field": field,
                                    "old": django_value,
                                    "new": peewee_value
                                }
                            })
                            setattr(ingredient_obj, field, peewee_value)
                            ingredient_obj.save()
                    else:
                        task.increment_errors(
                            logger = logger,
                            message = f"Field {field} does not exist in Django IngredientQuantity model."
                        )
            else:
                # Create new ingredient and quantity

                _ingredient, created = Ingredient.objects.get_or_create(name=ingredient_name)


                _ingredient_quantity = IngredientQuantity.objects.create(
                    ingredient=_ingredient,
                    recipe=__recipe,
                    quantity_original=item.get('quantity_original'),
                    quantity_normalized=item.get('quantity_normalized'),
                    units_normalized=item.get('units_normalized'),
                    extra_quantity=item.get('extra_quantity'),
                    extra_units=item.get('extra_units')
                )
                mapped_fields['ingredients_quantity'].append({
                    "created": {
                        "ingredient": ingredient_name,
                        "quantity_original": item.get('quantity_original'),
                        "quantity_normalized": item.get('quantity_normalized'),
                        "units_normalized": item.get('units_normalized'),
                        "extra_quantity": item.get('extra_quantity'),
                        "extra_units": item.get('extra_units')
                    }
                })

        
        " Check for changes in Useful Tools "
        mapped_fields['useful_tools'] = []

        # Create dictionaries for quick lookup of existing and incoming useful tools
        existing_useful_tools_dict = {useful_tool.text: useful_tool for useful_tool in __recipe.useful_tools.all()}
        incoming_useful_tools_dict = {item['text']: item for item in _useful_tools}

        # Identify and delete removed useful tools
        for text, useful_tool_obj in existing_useful_tools_dict.items():
            if text not in incoming_useful_tools_dict:
                mapped_fields['useful_tools'].append({
                    "deleted": {
                        "id": useful_tool_obj.id,
                        "text": text
                    }
                })
                __recipe.useful_tools.remove(useful_tool_obj)
                __recipe.save()

        # Process incoming useful tools
        for text, item in incoming_useful_tools_dict.items():
            if text in existing_useful_tools_dict:
                # Update existing useful tool and check for changes
                useful_tool_obj = existing_useful_tools_dict[text]
                for field in ['text']:
                    if hasattr(UsefulTool, field):
                        peewee_value = item.get(field)
                        django_value = getattr(useful_tool_obj, field, None)
                        if peewee_value != django_value:
                            mapped_fields['useful_tools'].append({
                                "updated": {
                                    "field": field,
                                    "old": django_value,
                                    "new": peewee_value
                                }
                            })
                            setattr(useful_tool_obj, field, peewee_value)
                            useful_tool_obj.save()
                    else:
                        task.increment_errors(
                            logger = logger,
                            message = f"Field {field} does not exist in Django UsefulTool model."
                        )
            else:
                # Create new useful tool
                _useful_tool, created = UsefulTool.objects.get_or_create(text=text)
                _useful_tool.recipes.add(__recipe)
                _useful_tool.save()
                mapped_fields['useful_tools'].append({
                    "created": {
                        "text": text
                    }
                })
                    
        
        " Check for changes in Tags "
        mapped_fields['tags'] = []

        # Create dictionaries for quick lookup of existing and incoming tags
        existing_tags_dict = {tag.text: tag for tag in __recipe.tags.all()}
        incoming_tags_dict = {item['tag']['text']: item for item in _tag_recipe_through}

        # Identify and delete removed tags
        for title, tag_obj in existing_tags_dict.items():
            if title not in incoming_tags_dict:
                mapped_fields['tags'].append({
                    "deleted": {
                        "id": tag_obj.id,
                        "text": title
                    }
                })
                __recipe.tags.remove(tag_obj)
                __recipe.save()

        # Process incoming tags
        for text, item in incoming_tags_dict.items():
            if text in existing_tags_dict:
                # Update existing tag and check for changes
                tag_obj = existing_tags_dict[text]

                for field in ['text']:
                    if hasattr(Tag, field):
                        peewee_value = item['tag'].get(field)
                        django_value = getattr(tag_obj, field, None)
                        if peewee_value != django_value:
                            mapped_fields['tags'].append({
                                "updated": {
                                    "field": field,
                                    "old": django_value,
                                    "new": peewee_value
                                }
                            })
                            setattr(tag_obj, field, peewee_value)
                            tag_obj.save()
                    else:
                        task.increment_errors(
                            logger = logger,
                            message = f"Field {field} does not exist in Django Tag model."
                        )
            else:
                # Create new tag
                _tag, created = Tag.objects.get_or_create(text=text)
                __recipe.tags.add(_tag)
                __recipe.save()
                mapped_fields['tags'].append({
                    "created": {
                        "text": text
                    }
                })
        
        
                    
        " Check for changes in Nutrition Information "
        mapped_fields['nutrition_information'] = []

        if _nutrition_information:
            if __recipe.nutrition_information:
                # Update existing Nutrition Information and check for changes
                for field, peewee_value in _nutrition_information.items():
                    peewee_value_float = float(peewee_value)
                    if hasattr(NutritionInformation, field):
                        django_value = getattr(__recipe.nutrition_information, field, None)
                        if peewee_value_float != django_value:
                            mapped_fields['nutrition_information'].append({
                                "updated": {
                                    "field": field,
                                    "old": django_value,
                                    "new": peewee_value_float
                                }
                            })
                            setattr(__recipe.nutrition_information, field, peewee_value)
                            __recipe.nutrition_information.save()
                    else:
                        task.increment_errors(
                            logger = logger,
                            message = f"Field {field} does not exist in Django NutritionInformation model."
                        )
            else:
                # Create new Nutrition Information
                new_nutrition_info = NutritionInformation.objects.create(
                    energy_kcal=_nutrition_information.get('energy_kcal'),
                    energy_perc=_nutrition_information.get('energy_perc'),
                    carbohydrates_g=_nutrition_information.get('carbohydrates_g'),
                    carbohydrates_perc=_nutrition_information.get('carbohydrates_perc'),
                    sugars_g=_nutrition_information.get('sugars_g'),
                    sugars_perc=_nutrition_information.get('sugars_perc'),
                    fat_g=_nutrition_information.get('fat_g'),
                    fat_perc=_nutrition_information.get('fat_perc'),
                    saturates_g=_nutrition_information.get('saturates_g'),
                    saturates_perc=_nutrition_information.get('saturates_perc'),
                    protein_g=_nutrition_information.get('protein_g'),
                    protein_perc=_nutrition_information.get('protein_perc'),
                    salt_g=_nutrition_information.get('salt_g'),
                    salt_perc=_nutrition_information.get('salt_perc'),
                    fiber_g=_nutrition_information.get('fiber_g')
                )
                __recipe.nutrition_information = new_nutrition_info
                __recipe.save()

                mapped_fields['nutrition_information'].append({
                    "created": {
                        "nutrition_information": _nutrition_information
                    }
                })
                
        " Check for changes in RecipeAuditLog "
        
        # Remove empty lists from mapped_fields
        mapped_fields = {key: value for key, value in mapped_fields.items() if value}
        
        if mapped_fields :
            logger.info(f"Recipe {recipe.id} has changes.")
            
            # Check if the recipe is verified and create audit logs accordingly
            if __recipe.verified:
                __recipe.verified = False
                __recipe.save()
                
                for field, changes in mapped_fields.items():
                    if isinstance(changes, list):
                        for change in changes:
                            if 'created' in change:
                                create_audit_log(RecipeAuditLog.Type.Update, task, __recipe, field=field, old_value=None, new_value=change['created'], update_sub_type=RecipeAuditLog.SubType.Create)
                            elif 'deleted' in change:
                                create_audit_log(RecipeAuditLog.Type.Update, task, __recipe, field=field, old_value=change['deleted'], new_value=None, update_sub_type=RecipeAuditLog.SubType.Delete)
                            elif 'updated' in change:
                                create_audit_log(RecipeAuditLog.Type.Update, task, __recipe, field=field, old_value=change['updated']['old'], new_value=change['updated']['new'], update_sub_type=RecipeAuditLog.SubType.Update)
                    else:
                        create_audit_log(RecipeAuditLog.Type.Update, task, __recipe,field=field, old_value=changes['old'], new_value=changes['new'], update_sub_type=RecipeAuditLog.SubType.Update) 
                    
            else:
                # If recipe is not verified, check for created AuditLog and update it
                audit_logs_created_count = RecipeAuditLog.objects.filter(recipe=__recipe, type=RecipeAuditLog.Type.Create, accepted =False ).count()
                
                if audit_logs_created_count == 1:
                    create_audit_log(RecipeAuditLog.Type.Create, task, __recipe)                
                else:
                    task.increment_errors(
                        logger = logger,
                        message = f"Recipe {recipe.id} has changes isn't verified, and no created AuditLog. There are {audit_logs_created_count} Create Audit Logs it should be one."
                    )
        
        
            
    logger.info("")
    
    
def persist_recipe(logger, task, recipe, recipe_t):
       
    " Recipe "
    
    logger.info(f"Persisting Recipe {recipe.id}.")
    
    recipe.title = recipe_t['title']
    recipe.description = recipe_t['description']

    recipe.difficulty = recipe_t['difficulty']
    recipe.portion_lower = recipe_t['portion_lower']
    recipe.portion_upper = recipe_t['portion_upper']
    recipe.portion_units = recipe_t['portion_units']
    recipe.time = recipe_t['time']
    recipe.time_units = recipe_t['time_units']
    
    recipe.source_rating = recipe_t['source_rating']
    recipe.source_link = recipe_t['source_link']
    
    recipe.image = f"{FIREBASE_STORAGE_COMPANY_BUCKET}{lower_and_underscore(COMPANY_CONTINENTE)}/recipes/{recipe_t['image'].split('/')[-1]}"
    recipe.video_link = recipe_t['video_link']
    
    try:
        send_image_to_firebase(
            open(recipe_t['image'], "rb").read(),
            recipe.image
        )
    except FileNotFoundError as exception:
        task.increment_errors(
            logger = logger,
            message = "Failed to found Image.",
            stack_trace=traceback.format_exc()
        )
    
    recipe.save()
    
    " Nutrition Information "
    
    if recipe_t['nutrition_information']:
        _nutrition_information = NutritionInformation.objects.create(
            energy_kcal=recipe_t['nutrition_information']['energy_kcal'],   
            energy_perc=recipe_t['nutrition_information']['energy_perc'],
            carbohydrates_g=recipe_t['nutrition_information']['carbohydrates_g'],
            carbohydrates_perc=recipe_t['nutrition_information']['carbohydrates_perc'],
            sugars_g=recipe_t['nutrition_information']['sugars_g'],
            sugars_perc=recipe_t['nutrition_information']['sugars_perc'],
            fat_g=recipe_t['nutrition_information']['fat_g'],
            fat_perc=recipe_t['nutrition_information']['fat_perc'],
            saturates_g=recipe_t['nutrition_information']['saturates_g'],
            saturates_perc=recipe_t['nutrition_information']['saturates_perc'],
            protein_g=recipe_t['nutrition_information']['protein_g'],
            protein_perc=recipe_t['nutrition_information']['protein_perc'],
            salt_g=recipe_t['nutrition_information']['salt_g'],
            salt_perc=recipe_t['nutrition_information']['salt_perc'],
            fiber_g=recipe_t['nutrition_information']['fiber_g']
        )
        
        recipe.nutrition_information = _nutrition_information
        recipe.save()
    
    " Tag "
    
    for recipe_tag_through in recipe_t['tagrecipethrough_set']:
        _tag, created = Tag.objects.get_or_create(text = recipe_tag_through['tag']['text'])
        recipe.tags.add(_tag)
        recipe.save()
        
    " Preparation "
    _preparation = pickle.loads(recipe_t['preparation'])
    
    for step in _preparation:
        _preparation = Preparation(
            recipe=recipe,
            step=step['step'],
            description=step['description'],
            section=step['section']
        )
        _preparation.save()
        
    " Useful Tool "
    
    for useful_tool in recipe_t['useful_tools']:
        _useful_tool, created = UsefulTool.objects.get_or_create(text = useful_tool['text'])

        _useful_tool.recipes.add(recipe)
        _useful_tool.save()
    
    " Ingredient "
    for ingredient in recipe_t['ingredients']:

        _ingredient, created = Ingredient.objects.get_or_create(name = ingredient['ingredient']['name'])

        _ingredient_quantity = IngredientQuantity(
            ingredient=_ingredient,
            recipe=recipe,
            quantity_original=ingredient['quantity_original'],
            quantity_normalized=ingredient['quantity_normalized'],
            units_normalized=ingredient['units_normalized'],
            extra_quantity=ingredient['extra_quantity'],
            extra_units=ingredient['extra_units']
        )
        _ingredient_quantity.save()
    
    " RecipeAuditLog "
    
    create_audit_log(RecipeAuditLog.Type.Create, task, recipe)
    

def create_audit_log(type, task, recipe, field = None, old_value = None, new_value = None, update_sub_type:RecipeAuditLog.SubType = None):

    match type:
        case RecipeAuditLog.Type.Create:
            
            # In this case, we need to check if the recipe is already created
            # and if so, we just need to update the audit log.
            # If not, we create a new audit log.
            
            recipe_audit_log = RecipeAuditLog.objects.filter(
                recipe=recipe.id,
                type=RecipeAuditLog.Type.Create,        
            ).first()
            
            if not recipe_audit_log:
                recipe_audit_log = RecipeAuditLog(
                    recipe=recipe,
                    task=task,
                    type=type
                )

            recipe_audit_log.task = task
            recipe_audit_log.field = "class"
            recipe_audit_log.description = f'Create Recipe {recipe.id}'
            recipe_audit_log.new_value = RecipeSerializer(recipe).data
            
            
        case RecipeAuditLog.Type.Update:
            
            if not field:
                raise ValueError("Attribute field is required for updating a recipe.")
            
            if not update_sub_type:
                raise ValueError("Attribute update_sub_type is required for updating a recipe.")
            
            recipe_audit_log, created = RecipeAuditLog.objects.get_or_create(
                        recipe=recipe,
                        field=field,
                        type=RecipeAuditLog.Type.Update,
                    )
            
            recipe_audit_log.field = field
            recipe_audit_log.old_value = old_value
            recipe_audit_log.new_value = new_value
            recipe_audit_log.task = task
            recipe_audit_log.update_sub_type = update_sub_type
            
            recipe_audit_log.description = f'Updated {field} Recipe {recipe.id}'
    
        case RecipeAuditLog.Type.Delete:
            
            # In this case, we need to check if the recipe is already deleted
            # and if so, we just need to update the audit log.
            # If not, we create a new audit log.
            
            recipe_audit_log = RecipeAuditLog.objects.filter(
                recipe=recipe.id,
                task=task.id,
                type=RecipeAuditLog.Type.Create,        
            ).first()
            
            if not recipe_audit_log:
                recipe_audit_log = RecipeAuditLog(
                    recipe=recipe,
                    task=task,
                    type=type
                )

            recipe_audit_log.field = "class"
            recipe_audit_log.description = f'Delete Recipe {recipe.id}'
            recipe_audit_log.old_value = RecipeSerializer(recipe).data
        
    recipe_audit_log.save()
    

