from django.core.management import call_command
from django.core.management.base import BaseCommand

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
        
        self.stdout.write(self.style.SUCCESS('Install gecko driver...'))
        call_command('install_geckodriver')
        
        self.stdout.write(self.style.SUCCESS('All commands executed successfully!'))