
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

from apps.common.tests.functions import print_prologue, create_test_users, create_test_company
from apps.etl_app.tasks import _reap_zombie_tasks


##
#   Contants
#

from apps.common.constants import COMPANY_CONTINENTE, COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD
from apps.common.tests.constants import TESTING_ACCOUNT_A, TESTING_ACCOUNT_A_PASSWORD, TESTING_ACCOUNT_B, TESTING_ACCOUNT_B_PASSWORD, TESTING_ACCOUNT_C, TESTING_ACCOUNT_C_PASSWORD
from apps.common.models import ProcessType


###
#
#       Task Views 
#   
##

from apps.etl_app.views import TaskTableView
from unittest.mock import patch, MagicMock




###
#
#       Task Load Recipes Tests 
#   
##


class TaskLoadRecipesTestCase(TestCase):
    
    def __loop_full_process(self):
        " Loop a full process with Extract, Transform and Load stages for testing. "
        
        # Extract Stage
        extract_job = Job.objects.create(
            type=Job.TaskType.EXTRACT,
            process=ProcessType.RECIPES,
            name=f'Test Extract Job {datetime.now().timestamp()}',
            company=self.company_continente,
            created_by= self.user_a,
            stopping_condition= self.threshold_stopping_condition
        )
        
        self.extract_task = Task.objects.create(
            type=Task.TaskType.EXTRACT,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            owner_job=extract_job,
            debug_mode=True
        )
        self.extract_task = self.extract_task.launch()
        
        # Transform Stage
        transform_job = Job.objects.create(
            type=Job.TaskType.TRANSFORM,
            process=ProcessType.RECIPES,
            name=f'Test Transform Job {datetime.now().timestamp()}',
            company=self.company_continente,
            created_by= self.user_a,
            stopping_condition= self.threshold_stopping_condition
        )
        
        self.transform_task = Task.objects.create(
            type=Task.TaskType.TRANSFORM,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            owner_job=transform_job,
            parent_task=self.extract_task,
            debug_mode=True
        )
        self.transform_task = self.transform_task.launch()
        
        # Load Stage
        self.load_job = Job.objects.create(
            type=Job.TaskType.LOAD,
            process=ProcessType.RECIPES,
            name=f'Test Load Job {datetime.now().timestamp()}',
            company=self.company_continente,
            created_by= self.user_a,
            stopping_condition= self.threshold_stopping_condition
        )
        
        self.load_task = Task.objects.create(
            type=Task.TaskType.LOAD,
            process=ProcessType.RECIPES,
            company=self.company_continente,
            owner_job=self.load_job,
            parent_task=self.transform_task,
            debug_mode=True
        )
        self.load_task = self.load_task.launch()
    
    def setUp(self):
        """ Set up a Comapny for testing."""
        
        # Create predefined users A, B, C
        create_test_users(self)
        
        # Create a company for testing
        create_test_company(self)
        
        # Create a user for the company
        self.user_continente = User.objects.create(
            name=COMPANY_CONTINENTE,
            email=f"{COMPANY_CONTINENTE}@{COMPANY_CONTINENTE}.pt",
            is_staff=True,
            is_superuser=False,
        )
        self.user_b.set_password(COMPANY_CONTINENTE_DEFAULT_USER_PASSWORD)
        self.user_b.save()
        
        # Create a company 
        self.company_continente = Company.objects.create(
            name=COMPANY_CONTINENTE
        )
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
            item.accept(changed_by = self.user_a)
        
         
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
    
        
    
    
        def test_load_recipes_on_a_update(self):
        """ Test that Load Continente Recipes logs updates correctly when a recipe is updated."""
        print_prologue()

        # Accept all audit logs to simulate a user accepting changes
        for item in RecipeAuditLog.objects.all():
            item.accept(changed_by = self.user_a)
        
         
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

          
        
        

class TaskTableViewTestCase(TestCase):
    
    
    
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
