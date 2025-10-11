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
from django.test import override_settings
import unittest

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

from apps.user_app.models import User, Invitation, Company



##
#   Serializers
#


##
#   Forms
#


##
#   Functions
#

from apps.common.tests.functions import print_prologue, create_test_users, create_test_company, perm_string


##
#   Contants
#

from apps.common.tests.constants import *
from apps.user_app.constants import GROUPS_PERMISSIONS


###
#
#       Base Test Case
#   
##



class _BaseViewTestCase(TestCase):
    """Custom TestCase with a default setup for authenticated user testing."""
    url = None
    template_name = None
    
    # The specific permission to test for this view
    permission = None
    permission_ = None
    
    # Test Users
    placeholder = None
    company_user = None
    normal_user = None
    company_staff_user = None
    company_admin_user = None
    app_staff_user = None
    app_admin_user = None


    
    def setUp(self):
        """Set up test environment with users, groups, and permissions."""
        self.company = create_test_company(name="Good Bites")
        create_test_users(self, self.company)  

    def assertValidSetup(self):
        if not self.url or not self.template_name:
            self.skipTest("Subclasses must define self.url and self.template_name, this should won't be relevant if this is a base class")
    
    def test_page_renders_correctly_authed(self):
        """Test that the company create page renders correctly for authenticated users with permissions."""
        self.assertValidSetup()
        
        print_prologue()
        
        # Login as superuser with permissions
        self.client.force_login(self.app_admin_user)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")
    
    def test_page_renders_correctly_not_authed(self):
        """Test that the company create page redirects unauthenticated users."""
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/login?next={self.url}")
        
        print("\n")
    
    def check_user_permission_and_response(self, user, expected_status_code, should_have_permission=False):
        """Generic helper to test user permissions and response status."""
        print_prologue()
        
        # Log in as the given user
        self.client.force_login(user)

        # Check which group the user belongs to
        user_groups = list(user.groups.values_list('name', flat=True))
        self.assertEqual(len(user_groups), 1)
        self.assertEqual(user_groups[0], user.type)
        
        # Check if permission is set correctly
        if should_have_permission:
            self.assertIn(self.permission, GROUPS_PERMISSIONS[user.type], f"User with UserType '{user.type}' should have permission '{self.permission}' but does not.")
        else:
            self.assertNotIn(self.permission, GROUPS_PERMISSIONS[user.type], f"User with UserType '{user.type}' should not have permission '{self.permission}' but does.")

        # Check if the user has the required permission
        user_permissions = user.get_all_permissions()
        has_permission = user.has_perm(self.permission_)
        
        self.assertEqual(has_permission, should_have_permission, f"User with UserType '{user.type}' permission check mismatch for '{self.permission}' defined in Security Rules.")

        # Use the Django test client to hit the URL
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, expected_status_code, f"User with UserType '{user.type}' expected status {expected_status_code} but got {response.status_code}")

        print("\n")
        
    def check_user_button_permission(self, expected_options, response):

    
        # Check if the dropdown options are present in the response content
        for option, permission in expected_options.items():
            self.assertTrue(response.context[permission]) # Decode the response content
            self.assertContains(response, option, msg_prefix = f"Expected option '{option}' not found in response.")
        
        # Check that no unexpected options are present
        for option in self.buttons:
            if option not in expected_options:
                self.assertNotRegex(
                    response.content.decode(),
                    rf"\b{option}\b",
                    msg=f"Unexpected option '{option}' found in response."
                )
        
    
class _BaseViewFunctionTestCase(TestCase):
    """Custom TestCase with a default setup for authenticated user testing."""
    url = None
    template_name = None
    
    # The specific permission to test for this view
    permission = None
    permission_ = None
    
    # Test Users
    placeholder = None
    company_user = None
    normal_user = None
    company_staff_user = None
    company_admin_user = None
    app_staff_user = None
    app_admin_user = None
    
    def setUp(self):
        """Set up test environment with users, groups, and permissions."""
        
        self.company = create_test_company(name="GoodBites")
        create_test_users(self, self.company)
    
    def assertValidSetup(self):
        if not self.url:
            self.skipTest("Subclasses must define self.url and self.template_name, this should won't be relevant if this is a base class")
    
    def test_page_renders_correctly_not_authed(self):
        """Test that the company create page redirects unauthenticated users."""
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/login?next={self.url}")
        
        print("\n")
        
    def check_user_permission_and_response(self, user, expected_status_code, should_have_permission=False):
        """Generic helper to test user permissions and response status."""
        print_prologue()
        
        # Log in as the given user
        self.client.force_login(user)

        # Check which group the user belongs to
        user_groups = list(user.groups.values_list('name', flat=True))
        self.assertEqual(len(user_groups), 1)
        self.assertEqual(user_groups[0], user.type)
        
        # Check if permission is set correctly
        if should_have_permission:
            self.assertIn(self.permission, GROUPS_PERMISSIONS[user.type], f"User with UserType '{user.type}' should have permission '{self.permission}' but does not.")
        else:
            self.assertNotIn(self.permission, GROUPS_PERMISSIONS[user.type], f"User with UserType '{user.type}' should not have permission '{self.permission}' but does.")

        # Check if the user has the required permission
        permissions = user.get_all_permissions()
        has_permission = user.has_perm(self.permission_)
        
        self.assertEqual(has_permission, should_have_permission, f"User with UserType '{user.type}' permission check mismatch for '{self.permission}' defined in Security Rules.")

        # Use the Django test client to hit the URL
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, expected_status_code, f"User with UserType '{user.type}' expected status {expected_status_code} but got {response.status_code}")

        print("\n")