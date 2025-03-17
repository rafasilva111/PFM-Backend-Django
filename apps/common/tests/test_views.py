
###
#       General imports
##


##
#   Default
#

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Group, Permission

##
#   Extras
#

import inspect


###
#       App specific imports
##


##
#   Models
#

from apps.user_app.models import User



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



##
#   Contants
#

from apps.common.tests.constants import TESTING_ACCOUNT_A, TESTING_ACCOUNT_A_PASSWORD, TESTING_ACCOUNT_B, TESTING_ACCOUNT_B_PASSWORD, TESTING_ACCOUNT_C, TESTING_ACCOUNT_C_PASSWORD


###
#
#       Base Test Case
#   
##

class BaseTestCase(TestCase):
    """Custom TestCase with a default setup for authenticated user testing."""
    
    
    def setUp(self):
        """Set up test environment with users, groups, and permissions."""
        # Create predefined users A, B, C
        for name, is_staff, is_superuser, password in [
            (TESTING_ACCOUNT_A, True, True, TESTING_ACCOUNT_A_PASSWORD),
            (TESTING_ACCOUNT_B, True, False, TESTING_ACCOUNT_B_PASSWORD),
            (TESTING_ACCOUNT_C, False, False, TESTING_ACCOUNT_C_PASSWORD),
        ]:
            email = f"{name}@{name}.pt"
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User(
                    name=name,
                    email=email,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
                user.set_password(password)
                user.save()

        # Define permissions for each group
        groups_permissions = {
            "Normal": [
                "can_view_task", "can_view_tasks",
                "can_view_job", "can_view_jobs",
            ],
            "Staff": [
                "can_view_task", "can_view_tasks", "can_restart_task", "can_cancel_task",
                "can_pause_task", "can_resume_task",
                "can_view_job", "can_view_jobs", "can_pause_job", "can_resume_job",
            ],
            "SuperUser": [
                "can_view_task", "can_view_tasks", "can_restart_task", "can_cancel_task",
                "can_create_task", "can_edit_task", "can_delete_task", "can_pause_task", "can_resume_task",
                "can_view_job", "can_view_jobs", "can_create_job", "can_edit_job",
                "can_delete_job", "can_pause_job", "can_resume_job",
            ],
        }

        # Predefined user-to-group mapping
        users_to_groups = {
            "Normal": [f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt"],
            "Staff": [f"{TESTING_ACCOUNT_B}@{TESTING_ACCOUNT_B}.pt"],
            "SuperUser": [f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt"],
        }

        # Create groups and assign permissions
        for group_name, perm_codes in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)

            # Assign permissions to the group
            permissions = Permission.objects.filter(codename__in=perm_codes)
            group.permissions.set(permissions)
            group.save()

        # Assign users to groups
        for group_name, emails in users_to_groups.items():
            try:
                group = Group.objects.get(name=group_name)
                for email in emails:
                    try:
                        user = User.objects.get(email=email)
                        user.groups.add(group)
                    except User.DoesNotExist:
                        print(f"User '{email}' does not exist")
            except Group.DoesNotExist:
                print(f"Group '{group_name}' does not exist")
        





###
#
#       Login Views 
#   
##

USER_EMAIL = "test@example.com"
USER_PASSWORD = "securepassword"


class LoginViewTest(TestCase):
    def setUp(self):
        """Set up a user for testing."""
                
        self.user = User.objects.create_user(
            email=USER_EMAIL,
            password=USER_PASSWORD,
            birth_date=timezone.now(),
        )
        self.login_url = reverse('login')  # Assuming the URL name for login is 'login'

    def test_login_page_loads_successfully(self):
        """Test that the login page loads and returns a 200 status."""
        
        print_prologue()
        
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/auth/login.html')
        self.assertContains(response, "Login")
        
        print("\n")
        
    def test_login_valid_credentials(self):
        """Test that a user can log in with valid credentials."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': USER_EMAIL,
            'password': USER_PASSWORD,
            'remember_me': 'on',
        })
        self.assertRedirects(response, reverse('home'))  # Assuming successful login redirects to 'home'
        
        print("\n")

    def test_login_invalid_credentials(self):
        """Test that invalid login credentials show the proper error."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'wrong@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")
        self.assertTemplateUsed(response, 'common/auth/login.html')
        
        print("\n")

    def test_login_no_credentials(self):
        """Test that the form shows errors if no credentials are submitted."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': '',
            'password': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")  # Assuming form validation messages
        self.assertTemplateUsed(response, 'common/auth/login.html')
        
        print("\n")

    def test_remember_me_checked(self):
        """Test that session expiration is extended when 'remember_me' is checked."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'securepassword',
            'remember_me': True,
        })
        self.assertTrue(self.client.session.get_expiry_age() > 0)
        
        print("\n")

    def test_remember_me_not_checked(self):
        """Test that session expires when 'remember_me' is not checked."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'securepassword',
            'remember_me': False,
        })
        
        self.assertEqual(self.client.session.get_expire_at_browser_close(), True)  # Session should expire at browser close
        
        print("\n")

class LogoutViewTest(TestCase):
    def setUp(self):
        """Set up a user for testing."""

        self.user = User.objects.create_user(
            email=USER_EMAIL,
            password=USER_PASSWORD,
            birth_date=timezone.now(),  
        )
        
        self.login_url = reverse('login')  # Assuming the URL name for login is 'login'
        self.logout_url = reverse('logout')  # Assuming the URL name for logout is 'logout'
        
        # Log in the user and check if login was successful
        login_success = self.client.login(email=USER_EMAIL, password=USER_PASSWORD)
        self.assertTrue(login_success, "Login should be successful")

        # Check if the user is authenticated
        response = self.client.get(self.login_url)  # Fetching the login page to check authentication
        self.assertTrue(response.wsgi_request.user.is_authenticated, "User should be authenticated")

        

    def test_user_logout(self):
        """Test that the user can log out successfully."""
        
        print_prologue()
        
        # Make a GET request to the logout URL
        response = self.client.post(self.logout_url)
        
        # Check that the user is logged out
        self.assertRedirects(response, self.login_url)  # Assuming you redirect to login after logout
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        print("\n")
        