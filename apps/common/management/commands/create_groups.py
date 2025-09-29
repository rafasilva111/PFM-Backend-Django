from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from apps.user_app.models import User
from apps.user_app.constants import GROUPS_PERMISSIONS



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
                

        # Create groups and assign permissions
        for group_name, perm_codes in GROUPS_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)

            # Assign permissions to the group
            permissions = Permission.objects.filter(codename__in=perm_codes)
            group.permissions.set(permissions)
            group.save()

        # Assign users to groups
        for user in User.objects.all():
            try:
                group = Group.objects.get(name=user.type)
                user.groups.add(group)

            except Group.DoesNotExist:
                print(f"Group '{user.type}' does not exist")
        
        self.stdout.write(self.style.SUCCESS('Groups created and permissions assigned successfully.'))
