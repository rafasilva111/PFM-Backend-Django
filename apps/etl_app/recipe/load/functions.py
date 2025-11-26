# === Imports ===

import pickle
import traceback
import concurrent.futures
import threading

# === Custom Functions and Constants ===
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET, COMPANY_CONTINENTE
from apps.common.functions import send_image_to_firebase, lower_and_underscore
from apps.recipe_app.serializers import RecipeSerializer
from apps.recipe_app.models import RecipeAuditLog, Recipe, Tag, UsefulTool, Preparation, Ingredient, IngredientQuantity, NutritionInformation
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.functions import (
    start_db,
    check_if_task_stopped,
    check_task_stopping_condition,
    start_sub_db,
    print_header,
    print_sub_header,
    retry_db_operation,
)
from django.db import models

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]


def persist_recipe(logger, task, recipe, recipe_t):
    """
    Persists a newly created recipe from the transformed Peewee structure
    into the main Django database.

    Workflow:
        1. Logs recipe creation and writes all simple scalar fields.
        2. Uploads and normalizes recipe images into Firebase storage.
        3. Creates related nutrition information, if provided.
        4. Creates many-to-many relationships (tags, tools).
        5. Persists preparation steps and ingredient quantities.
        6. Generates an initial RecipeAuditLog entry.

    Args:
        logger (logging.Logger): Structured logger instance.
        task (Task): The ETL task instance used for tracking errors
                     and associating audit log entries.
        recipe (Recipe): The Django Recipe object being populated.
        recipe_t (dict): Dictionary representation of the Peewee recipe
                         (from `model_to_dict`, including nested structures).

    Returns:
        None

    Notes:
        - Uses bulk_create where applicable for performance.
        - Missing image files are logged as non-fatal task errors.
        - This method should only be called on uninitialized, new Recipe objects.
    """

    # === INITIALIZATION ======================================================
    # List of simple fields directly copied from transformed recipe
    SIMPLE_FIELDS = [
        "title", "description",
        "difficulty",
        "portion_lower", "portion_upper", "portion_units",
        "time", "time_units",
        "source_rating", "source_link",
        "video_link"
    ]

    # === STEP 1: SIMPLE FIELD POPULATION ====================================
    for field in SIMPLE_FIELDS:
        setattr(recipe, field, recipe_t.get(field))

    # Normalize & transform image path
    recipe.image = (
        f"{FIREBASE_STORAGE_COMPANY_BUCKET}"
        f"{lower_and_underscore(COMPANY_CONTINENTE)}/recipes/"
        f"{recipe_t['image'].split('/')[-1]}"
    )

    # Upload image to Firebase
    try:
        with open(recipe_t["image"], "rb") as f:
            send_image_to_firebase(f.read(), recipe.image)
    except FileNotFoundError:
        task.increment_errors(
            logger,
            "Failed to find image.",
            stack_trace=traceback.format_exc()
        )

    recipe.save()

    # === STEP 2: NUTRITION INFORMATION ======================================
    nutrition_data = recipe_t.get("nutrition_information")
    if nutrition_data:
        # Remove ID if present
        nutrition_data.pop("id", None)
        # Create new NutritionInformation entry
        nutrition_obj = NutritionInformation.objects.create(**nutrition_data)
        recipe.nutrition_information = nutrition_obj
        recipe.save()


    # === HELPER: GENERIC MANY-TO-MANY ADDER =================================
    def add_many_to_many(item_list, model, field, relation_manager):
        """
        Generic helper to create or fetch M2M objects based on
        a single identifying field (e.g., text=name).
        """
        for item in item_list:
            obj, _ = model.objects.get_or_create(**{field: item[field]})
            relation_manager.add(obj)

    # === STEP 3: TAGS ========================================================
    add_many_to_many(
        item_list=[i["tag"] for i in recipe_t["tagrecipethrough_set"]],
        model=Tag,
        field="text",
        relation_manager=recipe.tags
    )

    # === STEP 4: PREPARATION STEPS ==========================================
    preparation_list = pickle.loads(recipe_t["preparation"])

    Preparation.objects.bulk_create([
        Preparation(
            recipe=recipe,
            step=item["step"],
            description=item.get("description"),
            section=item.get("section")
        )
        for item in preparation_list
    ])

    # === STEP 5: USEFUL TOOLS ===============================================
    add_many_to_many(
        item_list=recipe_t["useful_tools"],
        model=UsefulTool,
        field="text",
        relation_manager=recipe.useful_tools
    )

    # === STEP 6: INGREDIENTS & QUANTITIES ===================================
    ingredient_quantities = []
    for ing in recipe_t["ingredients"]:
        ingredient_obj, _ = Ingredient.objects.get_or_create(
            name=ing["ingredient"]["name"]
        )

        ingredient_quantities.append(
            IngredientQuantity(
                ingredient=ingredient_obj,
                recipe=recipe,
                quantity_original=ing["quantity_original"],
                quantity_normalized=ing["quantity_normalized"],
                units_normalized=ing["units_normalized"],
                extra_quantity=ing["extra_quantity"],
                extra_units=ing["extra_units"]
            )
        )

    IngredientQuantity.objects.bulk_create(ingredient_quantities)

    # === STEP 7: AUDIT ENTRY =================================================
    create_audit_log(
        RecipeAuditLog.Type.Create,
        task,
        recipe
    )

 
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
    

