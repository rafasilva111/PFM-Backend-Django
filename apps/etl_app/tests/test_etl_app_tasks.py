
###
#       General imports
##


##
#   Default
#

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.test import RequestFactory

##
#   Extras
#
from datetime import datetime
import inspect


###
#       App specific imports
##


##
#   Models
#

from apps.user_app.models import User,Company
from apps.etl_app.models import Task, Job, ThresholdCondition
from apps.recipe_app.models import Recipe, RecipeAuditLog, Ingredient, IngredientQuantity, NutritionInformation, Tag, UsefulTool, Preparation

##
#   Serializers
#


##
#   Forms
#


##
#   Functions
#

from apps.common.tests.functions import print_prologue
from apps.etl_app.tasks import _reap_zombie_tasks
from apps.etl_app.functions import start_db

##
#   Contants
#

from apps.common.constants import COMPANY_CONTINENTE, COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD
from apps.common.tests.constants import *
from apps.common.models import ProcessType
from django.test import TestCase
from apps.common.tests.functions import create_test_company, create_test_task, create_test_users


###
#
#       Task Views 
#   
##

from apps.etl_app.views import TaskTableView
from unittest.mock import patch, MagicMock




###
#
#       Task Extract Recipes
#   
##

from apps.etl_app.constants import EXTRACT_CONTINENTE_RECIPES_DB
from apps.etl_app.recipe.extract.continente.main import models_ as recipe_continente_extract_models
from apps.etl_app.recipe.extract.continente.models import Recipe as ExtractContinenteRecipe, RecipeLink as ExtractContinenteRecipeLink, database_proxy as recipe_continenete_extract_database_proxy


class TaskExtractContinenteRecipesTestCase(TestCase):
    
    base_threshold_value = 13
    
    def setUp(self):
        """ Set up a Comapny for testing."""
        create_test_users(self)
        
        # Create a user for the company
        self.user_continente = User.objects.create(
            name=COMPANY_CONTINENTE,
            email=f"{COMPANY_CONTINENTE}@{COMPANY_CONTINENTE}.pt",
            is_staff=True,
            is_superuser=False,
        )
        self.user_continente.set_password(COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD)
        self.user_continente.save()
        
        # Create a company 
        self.company_continente = create_test_company( name = COMPANY_CONTINENTE)
        self.company_continente.processes.append(ProcessType.RECIPES.value)
        self.company_continente.user_account = self.user_continente
        self.company_continente.save()
        
        # Create a threshold stopping condition
        self.threshold_stopping_condition = ThresholdCondition.objects.create(
            threshold_value=self.base_threshold_value
        )
        
        # Extract Stage
        self.extract_job, self.extract_task = create_test_task(
            type=Job.TaskType.EXTRACT,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            user=self.app_admin_user,
            stopping_condition=self.threshold_stopping_condition
        )        
        
    def tearDown(self):
        self.extract_task.purge()

    def test_threshold_stopping_condition(self):
        """ Test that Extract Continente Recipes stops at the defined threshold."""
        print_prologue()
        
        # 1 - Test Extract Continente Recipes with threshold stopping condition
        self.extract_task = self.extract_task.launch()
        
        self.extract_task, database = start_db(
            logger=None,
            task=self.extract_task,
            models=recipe_continente_extract_models,
            path=EXTRACT_CONTINENTE_RECIPES_DB,
            database_proxy=recipe_continenete_extract_database_proxy,
            reset= False
        )

        self.assertEqual(ExtractContinenteRecipe.select().count(),self.threshold_stopping_condition.threshold_value)
        self.assertEqual(ExtractContinenteRecipeLink.select().count(),self.base_threshold_value)
        self.assertEqual(self.extract_task.step, self.threshold_stopping_condition.threshold_value)
        self.assertEqual(self.extract_task.status, Task.Status.PAUSED)
        
        # 2 - Resume the task and check if it processes the next batch correctly
        tenth_ingredient = (
            ExtractContinenteRecipe
            .select()
            .where(ExtractContinenteRecipe.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteRecipe.id)
            .get()
        )
        self.extract_task.resume()
        self.extract_task.refresh_from_db()
        
        tenth_ingredient_ = (
            ExtractContinenteRecipe
            .select()
            .where(ExtractContinenteRecipe.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteRecipe.id)
            .get()
        )
        self.assertEqual(tenth_ingredient.title, tenth_ingredient_.title)
        self.assertEqual(ExtractContinenteRecipe.select().count(),self.threshold_stopping_condition.threshold_value * 2)
        self.assertEqual(ExtractContinenteRecipeLink.select().count(),self.base_threshold_value * 2)
        self.assertEqual(self.extract_task.step, self.threshold_stopping_condition.threshold_value * 2)
        self.assertEqual(self.extract_task.status, Task.Status.PAUSED)
        
        #  Check if the last extracted recipe link is different from the one before the break
        left_break_ingredient_link = (
            ExtractContinenteRecipeLink
            .select()
            .where(ExtractContinenteRecipeLink.id == self.base_threshold_value)
            .order_by(ExtractContinenteRecipeLink.id)
            .get()
        )
        right_break_ingredient_link = (
            ExtractContinenteRecipeLink
            .select()
            .where(ExtractContinenteRecipeLink.id == self.base_threshold_value + 1)
            .order_by(ExtractContinenteRecipeLink.id)
            .get()
        )
        self.assertNotEqual(left_break_ingredient_link.link, right_break_ingredient_link.link)
        
        # Check if the last extracted recipe is different from the one before the break
        left_break_ingredient = (
            ExtractContinenteRecipe
            .select()
            .where(ExtractContinenteRecipe.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteRecipe.id)
            .get()
        )
        right_break_ingredient = (
            ExtractContinenteRecipe
            .select()
            .where(ExtractContinenteRecipe.id == self.threshold_stopping_condition.threshold_value + 1)
            .order_by(ExtractContinenteRecipe.id)
            .get()
        )
        self.assertNotEqual(left_break_ingredient.title, right_break_ingredient.title)
            


###
#
#       Task Extract Ingredients
#   
##

from apps.etl_app.constants import EXTRACT_CONTINENTE_INGREDIENTS_DB
from apps.etl_app.ingredient.extract.continente.main import models_ as ingredient_continente_extract_models, PAGE_LINKS_OFFSET as ingredient_continente_page_links_offset
from apps.etl_app.ingredient.extract.continente.models import Ingredient as ExtractContinenteIngredient, IngredientLink as ExtractContinenteIngredientLink, database_proxy as ingredient_continenete_extract_database_proxy


class TaskExtractContinenteIngredientsTestCase(TestCase):
    
    base_threshold_value = (ingredient_continente_page_links_offset/2 + 1) # base threshold value to extract half + 1 of the ingredients per page
    
    def setUp(self):
        """ Set up a Comapny for testing."""
        
        # Create basic users
        create_test_users(self)
        
        # Create a user for the company
        self.user_continente = User.objects.create(
            name=COMPANY_CONTINENTE,
            email=f"{COMPANY_CONTINENTE}@{COMPANY_CONTINENTE}.pt",
            is_staff=True,
            is_superuser=False,
        )
        self.user_continente.set_password(COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD)
        self.user_continente.save()
        
        # Create a company 
        self.company_continente = create_test_company( name = COMPANY_CONTINENTE)
        self.company_continente.processes.append(ProcessType.RECIPES.value)
        self.company_continente.user_account = self.user_continente
        self.company_continente.save()
        
        # Create a threshold stopping condition
        self.threshold_stopping_condition = ThresholdCondition.objects.create(
            threshold_value=self.base_threshold_value
        )
        
        # Extract Stage
        self.extract_job, self.extract_task = create_test_task(
            type=Job.TaskType.EXTRACT,
            process=ProcessType.INGREDIENTS,
            company=self.company_continente,
            user=self.app_admin_user,
            stopping_condition=self.threshold_stopping_condition
        )        
        
    def tearDown(self):
        self.extract_task.purge()

    def test_threshold_stopping_condition(self):
        """ Test that Extract Continente Recipes stops at the defined threshold."""
        print_prologue()
        
        # 1 - Test Extract Continente Recipes with threshold stopping condition
        self.extract_task = self.extract_task.launch()
        
        self.extract_task, database = start_db(
            logger=None,
            task=self.extract_task,
            models=ingredient_continente_extract_models,
            path=EXTRACT_CONTINENTE_INGREDIENTS_DB,
            database_proxy=ingredient_continenete_extract_database_proxy,
            reset= False
        )

        self.assertEqual(ExtractContinenteIngredient.select().count(),self.threshold_stopping_condition.threshold_value)
        self.assertEqual(ExtractContinenteIngredientLink.select().count(),self.base_threshold_value)
        self.assertEqual(self.extract_task.step, self.threshold_stopping_condition.threshold_value)
        self.assertEqual(self.extract_task.status, Task.Status.PAUSED)
        
        # 2 - Resume the task and check if it processes the next batch correctly
        tenth_ingredient = (
            ExtractContinenteIngredient
            .select()
            .where(ExtractContinenteIngredient.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteIngredient.id)
            .get()
        )
        self.extract_task.resume()
        self.extract_task.refresh_from_db()
        
        tenth_ingredient_ = (
            ExtractContinenteIngredient
            .select()
            .where(ExtractContinenteIngredient.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteIngredient.id)
            .get()
        )
        self.assertEqual(tenth_ingredient.title, tenth_ingredient_.title)
        self.assertEqual(ExtractContinenteIngredient.select().count(),self.threshold_stopping_condition.threshold_value * 2)
        self.assertEqual(ExtractContinenteIngredientLink.select().count(),self.base_threshold_value * 2)
        self.assertEqual(self.extract_task.step, self.threshold_stopping_condition.threshold_value * 2)
        self.assertEqual(self.extract_task.status, Task.Status.PAUSED)

        #  Check if the last extracted recipe link is different from the one before the break
        left_break_ingredient_link = (
            ExtractContinenteIngredientLink
            .select()
            .where(ExtractContinenteIngredientLink.id == self.base_threshold_value)
            .order_by(ExtractContinenteIngredientLink.id)
            .get()
        )
        right_break_ingredient_link = (
            ExtractContinenteIngredientLink
            .select()
            .where(ExtractContinenteIngredientLink.id == self.base_threshold_value + 1)
            .order_by(ExtractContinenteIngredientLink.id)
            .get()
        )
        self.assertNotEqual(left_break_ingredient_link.link, right_break_ingredient_link.link)
        
        # Check if the last extracted recipe is different from the one before the break
        left_break_ingredient = (
            ExtractContinenteIngredient
            .select()
            .where(ExtractContinenteIngredient.id == self.threshold_stopping_condition.threshold_value)
            .order_by(ExtractContinenteIngredient.id)
            .get()
        )
        right_break_ingredient = (
            ExtractContinenteIngredient
            .select()
            .where(ExtractContinenteIngredient.id == self.threshold_stopping_condition.threshold_value + 1)
            .order_by(ExtractContinenteIngredient.id)
            .get()
        )
        self.assertNotEqual(left_break_ingredient.title, right_break_ingredient.title)

        
        
###
#
#       Full Precess Test (Extract, Transform, Load)
#   
##

class TaskLoadRecipesTestCase(TestCase):
    
    def __loop_full_process(self):
        " Loop a full process with Extract, Transform and Load stages for testing. "
        
        # Extract Stage
        self.extract_job, self.extract_task = create_test_task(
            type=Job.TaskType.EXTRACT,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            user=self.app_admin_user,
            stopping_condition=self.threshold_stopping_condition
        )
        self.extract_task = self.extract_task.launch()
        
        # Transform Stage
        self.transform_job, self.transform_task = create_test_task(
            type=Job.TaskType.TRANSFORM,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            user=self.app_admin_user,
            parent_job=self.extract_job,
            stopping_condition=self.threshold_stopping_condition
        )
        self.transform_task = self.transform_task.launch()
        
        # Load Stage
        self.load_job, self.load_task = create_test_task(
            type=Job.TaskType.LOAD,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            user=self.app_admin_user,
            parent_job=self.transform_job,
            stopping_condition=self.threshold_stopping_condition
        )
        self.load_task = self.load_task.launch()
    
    def setUp(self):
        """ Set up a Comapny for testing."""
        
        # Create basic users
        create_test_users(self)
        
        # Create a user for the company
        self.user_continente = User.objects.create(
            name=COMPANY_CONTINENTE,
            email=f"{COMPANY_CONTINENTE}@{COMPANY_CONTINENTE}.pt",
            is_staff=True,
            is_superuser=False,
        )
        self.user_continente.set_password(COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD)
        self.user_continente.save()
        
        # Create a company 
        self.company_continente = create_test_company( name = COMPANY_CONTINENTE)
        self.company_continente.processes.append(ProcessType.RECIPES.value)
        self.company_continente.user_account = self.user_continente
        self.company_continente.save()
        
        # Create a threshold stopping condition
        self.threshold_stopping_condition = ThresholdCondition.objects.create(
            threshold_value=10
        )
        
             
        self.__loop_full_process()
    
    def tearDown(self):
        self.extract_task.purge()
        self.transform_task.purge()
        self.load_task.purge()
    
    def test_load_recipes_first_time(self):
        """ Test that Load Continente Recipes loads recipes correctly on first access."""
        print_prologue()
        
        self.assertEqual(Recipe.objects.count(),self.threshold_stopping_condition.threshold_value)
        self.assertEqual(RecipeAuditLog.objects.count(), self.threshold_stopping_condition.threshold_value )
        
        for recipe in Recipe.objects.all():
            self.assertFalse(recipe.verified)
            
        for recipe_audit_log in RecipeAuditLog.objects.all():
            self.assertEqual(recipe_audit_log.type, RecipeAuditLog.Type.Create)
    

     
    def test_load_recipes_on_a_update(self):
        """ Test that Load Continente Recipes logs updates correctly when a recipe is updated."""
        print_prologue()

        # Accept all audit logs to simulate a user accepting changes
        for item in RecipeAuditLog.objects.all():
            item.accept(changed_by = self.app_admin_user)
        
         
        # Update all fields of the first recipe
        recipe_test = Recipe.objects.first()
        recipe_test.title = "Updated Title"
        recipe_test.description = "Updated Description"
        recipe_test.image = "updated_image.jpg"
        recipe_test.video_link = "https://updated.video/link"
        recipe_test.difficulty = "Hard"
        recipe_test.portion_lower = "2"
        recipe_test.portion_upper = "4"
        recipe_test.portion_units = "servings"
        recipe_test.time = "45"
        recipe_test.time_units = "minutes"
        recipe_test.source_rating = 4.5
        recipe_test.save()
        
        # Nutrition Information
        if recipe_test.nutrition_information:
            recipe_test.nutrition_information.energy_kcal = 99999
            recipe_test.nutrition_information.energy_perc = 99999

            recipe_test.nutrition_information.fat_g = 99999
            recipe_test.nutrition_information.fat_perc = 99999

            recipe_test.nutrition_information.saturates_g = 99999
            recipe_test.nutrition_information.saturates_perc = 99999

            recipe_test.nutrition_information.carbohydrates_g = 99999
            recipe_test.nutrition_information.carbohydrates_perc = 99999

            recipe_test.nutrition_information.sugars_g = 99999
            recipe_test.nutrition_information.sugars_perc = 99999

            recipe_test.nutrition_information.fiber_g = 99999

            recipe_test.nutrition_information.protein_g = 99999
            recipe_test.nutrition_information.protein_perc = 99999

            recipe_test.nutrition_information.salt_g = 99999
            recipe_test.nutrition_information.salt_perc = 99999
            recipe_test.nutrition_information.save()
        ##
        #   Preparation
        #
        
        # Update
        preparation = recipe_test.preparation.first()
        if preparation:
            preparation.section = "Updated Section"
            preparation.step = 98
            preparation.description = "Updated Preparation Step"
            preparation.save()
        
        # Create
        recipe_test.preparation.create(
            section = "Updated Section",
            step = 99,
            description = "New Preparation Step"
        )
        
        ##
        #   Useful Tools
        #
        
        # Update
        useful_tool = recipe_test.useful_tools.first()
        if useful_tool:
            useful_tool.text = "Updated Useful Tool"
            useful_tool.save()
            
        # Create
        recipe_test.useful_tools.create(
            text = "New Useful Tool"
        )
        
        ##
        #   Ingredient / Ingredient Quantity
        #
        
        # Update
        ingredient_quantity = recipe_test.ingredients.first()
        if ingredient_quantity:
            ingredient_quantity.quantity_original = "999g"
            ingredient_quantity.quantity_normalized = 999.0
            ingredient_quantity.units_normalized = "g"
            ingredient_quantity.extra_quantity = 10.0
            ingredient_quantity.extra_units = "ml"
            ingredient_quantity.notes = "Updated Notes"
            ingredient_quantity.ingredient.name = "Updated Ingredient"
            ingredient_quantity.ingredient.save()
            ingredient_quantity.save()
        
        # Create
        ingredient = Ingredient.objects.create(
            name = "New Ingredient"
        )
        new_ingredient_quantity = recipe_test.ingredients.create(
            quantity_original = "100g",
            quantity_normalized = 100.0,
            units_normalized = "g",
            extra_quantity = 0.0,
            extra_units = "",
            ingredient = ingredient
        )
        
        ##
        #   Tag
        #
        # Update
        tag = recipe_test.tags.first()
        if tag:
            tag.text = "Updated Tag"
            tag.save()
        
        # Create
        recipe_test.tags.create(
            text = "New Tag"
        )
        
        # Re-run the load process to check if the update is logged
        self.__loop_full_process()

        audit_logs = RecipeAuditLog.objects.filter(type=RecipeAuditLog.Type.Update, recipe = recipe_test)
        audit_logs_count = audit_logs.count() # Filter out logs without changes
        
        self.assertEqual(audit_logs_count, 16)  # There should be 16 update logs (1 for each field changed)
        

        # Check that the audit log contains the updated fields
        title_updated = audit_logs.filter(field = "title").count()
        self.assertEqual(title_updated, 1)
        description_updated = audit_logs.filter(field = "description").count()
        self.assertEqual(description_updated, 1)
        image_updated = audit_logs.filter(field = "image").count()
        self.assertEqual(image_updated, 1)
        video_link_updated = audit_logs.filter(field = "video_link").count()
        self.assertEqual(video_link_updated, 1)
        difficulty_updated = audit_logs.filter(field = "difficulty").count()
        self.assertEqual(difficulty_updated, 1)
        portion_lower_updated = audit_logs.filter(field = "portion_lower").count()
        self.assertEqual(portion_lower_updated, 1)
        portion_upper_updated = audit_logs.filter(field = "portion_upper").count()
        self.assertEqual(portion_upper_updated, 1)
        portion_units_updated = audit_logs.filter(field = "portion_units").count()
        self.assertEqual(portion_units_updated, 1)
        time_updated = audit_logs.filter(field = "time").count()
        self.assertEqual(time_updated, 1)
        time_units_updated = audit_logs.filter(field = "time_units").count()
        self.assertEqual(time_units_updated, 1)
        source_rating_updated = audit_logs.filter(field = "source_rating").count()
        self.assertEqual(source_rating_updated, 1)
        
        
        preparation_updated = audit_logs.filter(field = "preparation").count()
        self.assertEqual(preparation_updated, 1)
        useful_tools_updated = audit_logs.filter(field = "useful_tools").count()
        self.assertEqual(useful_tools_updated, 1)
        ingredient_quantity_updated = audit_logs.filter(field = "ingredients_quantity").count()
        self.assertEqual(ingredient_quantity_updated, 1)
        tag_updated = audit_logs.filter(field = "tags").count()
        self.assertEqual(tag_updated, 1)
        nutrition_informationg_updated = audit_logs.filter(field = "nutrition_information").count()
        self.assertEqual(nutrition_informationg_updated, 1)
    
        
    
          
class ReapZombieTaskTestCase(TestCase):
    
    
    
    ##
    #   Testing View permissions
    #
    def test_reap_zombie_tasks_with_zombie_celery_ids(self):
        """Test that _reap_zombie_tasks cancels tasks with celery_task_id not in Celery active list."""
        print_prologue()

        # Create a running task with celery_task_id not in Celery
        zombie_task = Task.objects.create(type=Task.TaskType.EMPTY, status=Task.Status.RUNNING, celery_task_id='zombie456')

        # Patch Celery inspect to return no active tasks
        with patch('apps.etl_app.tasks.app.control.inspect') as mock_inspect:
            mock_inspect.return_value.active.return_value = {'worker1': []}
            # Patch cancel method to track calls
            with patch.object(Task, 'cancel', autospec=True) as mock_cancel:
                count = _reap_zombie_tasks()
                mock_cancel.assert_any_call(zombie_task)
                self.assertGreaterEqual(count, 1)

    def test_reap_zombie_tasks_no_running_tasks(self):
        """Test _reap_zombie_tasks when there are no running tasks."""
        print_prologue()

        # Ensure no running tasks
        Task.objects.all().delete()

        with patch('apps.etl_app.tasks.app.control.inspect') as mock_inspect:
            mock_inspect.return_value.active.return_value = {}
            count = _reap_zombie_tasks()
            self.assertEqual(count, 0)

    def test_reap_zombie_tasks_handles_multiple_workers(self):
        """Test _reap_zombie_tasks with multiple Celery workers."""
        print_prologue()

        # Create running tasks
        t1 = Task.objects.create(type=Task.TaskType.EMPTY, status=Task.Status.RUNNING, celery_task_id='id1')
        t2 = Task.objects.create(type=Task.TaskType.EMPTY, status=Task.Status.RUNNING, celery_task_id='id2')
        t3 = Task.objects.create(type=Task.TaskType.EMPTY, status=Task.Status.RUNNING, celery_task_id='id3')

        with patch('apps.etl_app.tasks.app.control.inspect') as mock_inspect, \
             patch.object(Task, 'cancel', autospec=True) as mock_cancel:
            mock_inspect.return_value.active.return_value = {
                'worker1': [{'id': 'id1'}],
                'worker2': [{'id': 'id2'}]
            }
            count = _reap_zombie_tasks()
            # Only t3 should be canceled
            mock_cancel.assert_any_call(t3)
            self.assertEqual(mock_cancel.call_count, 1)
            self.assertEqual(count, 1)
