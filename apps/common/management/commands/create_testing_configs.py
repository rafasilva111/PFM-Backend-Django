from django.core.management import call_command
from django.core.management.base import BaseCommand
from apps.etl_app.models import Task
from apps.recipe_app.models import RecipeAuditLog, Recipe, RecipeReport
from apps.user_app.models import User
from apps.common.tests.constants import TESTING_ACCOUNT_APP_STAFF

class Command(BaseCommand):
    help = 'Run all management commands to set up test users, staging companies, automation accounts, groups, and a company'

    def handle(self, *args, **kwargs):
                
        self.stdout.write(self.style.SUCCESS('Creating default company...'))
        call_command('create_default_company')
        
        self.stdout.write(self.style.SUCCESS('Starting to create test users...'))
        call_command('create_test_users')
        
        self.stdout.write(self.style.SUCCESS('Creating staging companies...'))
        call_command('create_staging_companies')
        
        self.stdout.write(self.style.SUCCESS('Creating staging automation account...'))
        call_command('create_staging_automation_account')
        
        self.stdout.write(self.style.SUCCESS('Creating user groups...'))
        call_command('create_groups', assign_test_users=True)
        
        self.stdout.write(self.style.SUCCESS('Installing Gecko Driver...'))
        call_command('install_geckodriver')
        
        self.stdout.write(self.style.SUCCESS('Creating a test Task...'))
        test_task, created = Task.objects.get_or_create(
            type=Task.TaskType.EMPTY,
        )
        
        self.stdout.write(self.style.SUCCESS('Creating a test Recipe...'))
        test_recipe, created = Recipe.objects.get_or_create(
            title="Test Recipe",
            description="This is a test recipe.",
        )
        
        self.stdout.write(self.style.SUCCESS('Creating a test Audit Log...'))
        test_audit_log = RecipeAuditLog.objects.get_or_create(
            recipe=test_recipe,
            task=test_task,
            description="This is a test audit log.",
            type=RecipeAuditLog.Type.Create,
            sub_type=RecipeAuditLog.SubType.NONE,
        )
            
        
        self.stdout.write(self.style.SUCCESS('Creating a test Recipe Report...'))
        recipe_report = RecipeReport.objects.get_or_create(
            title="Test Recipe Report",
            message="This is a test recipe report.",
            recipe=test_recipe,
            user=User.objects.get(email=f"{TESTING_ACCOUNT_APP_STAFF}@{TESTING_ACCOUNT_APP_STAFF}.pt")
        )
        
        
        
        self.stdout.write(self.style.SUCCESS('All commands executed successfully!'))