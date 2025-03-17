from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from apps.user_app.models import User
from apps.common.constants import TESTING_ACCOUNT_A, TESTING_ACCOUNT_B,  TESTING_ACCOUNT_C
from apps.common.functions import lower_and_underescore



class Command(BaseCommand):
    """
    Django management command to create user groups with specific permissions and
    optionally assign predefined users to these groups.

    Groups created:
      - Normal: Basic user group with minimal permissions
      - Staff: Group with add, change, and view permissions on users
      - SuperUser: Group with full permissions on users (add, change, delete, view)

    Usage:
      - To create groups and set permissions only:
        python manage.py create_groups

      - To create groups, set permissions, and assign users to groups:
        python manage.py create_groups --assign-test-users
    """
    
    help = 'Create user groups with specific permissions, optionally assign users to groups'

    def add_arguments(self, parser):
        """
        Define command-line options for this command.

        Options:
          --assign-test-users : Boolean flag to indicate if users should be assigned to groups.
                           If this flag is present, predefined users will be associated
                           with the respective groups.
        """
        parser.add_argument(
            '--assign-test-users',
            action='store_true',
            help='If specified, assigns predefined users to groups',
        )

    def handle(self, *args, **options):
        """
        Main function to execute the command.

        - Creates groups with specified permissions.
        - If the --assign-test-users flag is provided, assigns predefined users to the created groups.

        Steps:
          1. Define groups and permissions, and create groups if they don't exist.
          2. Set permissions for each group.
          3. Optionally assign users to groups based on the --assign-test-users flag.
        """
        # Define groups and their permissions
        groups_permissions = {
            User.UserType.NORMAL: [
                # User permissions
                "can_view_user","can_view_users"
                # Task permissions
                "can_view_task","can_view_tasks",
                # Job permissions
                "can_view_job","can_view_jobs"
            ],
            User.UserType.STAFF: [
                # User permissions
                "can_view_user","can_view_users","can_invite_user","can_edit_user","can_delete_user","can_disable_user",
                # Task permissions
                "can_view_task","can_view_tasks","can_restart_task", "can_cancel_task", "can_pause_task", "can_resume_task",
                # Job permissions
                "can_view_job","can_view_jobs", "can_pause_job", "can_resume_job" 
            ],
            User.UserType.SUPERUSER: [
                # User permissions
                "can_view_user","can_view_users","can_invite_user","can_edit_user","can_delete_user","can_disable_user",
                # Task permissions
                "can_view_task","can_view_tasks","can_restart_task", "can_cancel_task", "can_create_task","can_edit_task","can_delete_task", "can_pause_task", "can_resume_task",
                # Job permissions
                "can_view_job","can_view_jobs", "can_create_job","can_edit_job","can_delete_job", "can_pause_job", "can_resume_job"
            ]
        }

        # Predefined users to groups mapping
        
        name_a = lower_and_underescore(TESTING_ACCOUNT_A)
        name_b = lower_and_underescore(TESTING_ACCOUNT_B)
        name_c = lower_and_underescore(TESTING_ACCOUNT_C)
        
        users_to_groups = {
            User.UserType.NORMAL: [f"{name_c}@{name_c}.pt"],
            User.UserType.STAFF: [f"{name_b}@{name_b}.pt" ],
            User.UserType.SUPERUSER: [f"{name_a}@{name_a}.pt"]
        }

        # Step 1: Create groups and assign permissions
        for group_name, perm_codes in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"Created group '{group_name}'")
            else:
                self.stdout.write(f"Group '{group_name}' already exists")

            # Set permissions for each group
            permissions = Permission.objects.filter(codename__in=perm_codes)
            group.permissions.set(permissions)
            group.save()

            self.stdout.write(f"Assigned permissions to group '{group_name}': {perm_codes}")

        # Step 2: Assign users to groups if --assign-test-users is specified
        if options['assign_test_users']:
            self.stdout.write("Assigning users to groups as per predefined mapping...")
            for group_name, emails in users_to_groups.items():
                try:
                    group = Group.objects.get(name=group_name)
                    for email in emails:
                        try:
                            user = User.objects.get(email=email)
                            user.user_type = group_name
                            user.save()
                            user.groups.add(group)
                            self.stdout.write(f"Added user '{email}' to group '{group_name}'")
                        except User.DoesNotExist:
                            self.stdout.write(f"User '{email}' does not exist")
                except Group.DoesNotExist:
                    self.stdout.write(f"Group '{group_name}' does not exist")
        else:
            self.stdout.write("Skipping user-group assignments as --assign-test-users was not specified.")

        self.stdout.write("Groups, permissions, and optional user assignments setup completed.")
