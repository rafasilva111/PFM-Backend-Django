
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

import inspect


###
#       App specific imports
##


##
#   Models
#

from apps.user_app.models import User
from apps.task_app.models import Task
from apps.common.tests.test_views import BaseTestCase


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
#       Task Views 
#   
##

from apps.task_app.views import TaskTableView

class TaskTableViewTestCase(BaseTestCase):
    def setUp(self):
        """Set up a user for testing."""

        super().setUp()
        self.factory = RequestFactory()
        self.request = self.factory.get("/customer/details")
        
        self.normal_user = User.objects.get(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt")
        self.staff_user = User.objects.get(email=f"{TESTING_ACCOUNT_B}@{TESTING_ACCOUNT_B}.pt")
        self.super_user = User.objects.get(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt")
        
        

        

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions_for_normal_user(self):
        """Test that a normal user can view tasks but cannot create, edit, or delete tasks."""
        
        print_prologue()
        
        self.request.user = self.normal_user
        
        response = TaskTableView.as_view()(self.request)
            
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_app/task/table.html')
        self.assertFalse(response.context['can_create_task'])
        self.assertFalse(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertFalse(response.context['can_delete_task'])
        
        print("\n")

    def test_view_permissions_for_staff_user(self):
        """Test that a staff user can view, edit, and pause tasks but cannot create or delete tasks."""
        
        print_prologue()
            
        login_success = self.client_staff_user.login(email=f"{TESTING_ACCOUNT_B}@{TESTING_ACCOUNT_B}.pt", password=TESTING_ACCOUNT_B_PASSWORD)
        self.assertTrue(login_success, "Login should be successful")
        
        response = self.client_staff_user.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_app/task/table.html')
        self.assertFalse(response.context['can_create_task'])
        self.assertFalse(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertFalse(response.context['can_delete_task'])
        
        print("\n")

    def test_view_permissions_for_super_user(self):
        """Test that a superuser can view, create, edit, and delete tasks."""
        
        print_prologue()
        
        if self.client:
            self.client.logout()
            
        login_success = self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        self.assertTrue(login_success, "Login should be successful")
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_app/task/table.html')
        self.assertTrue(response.context['can_create_task'])
        self.assertTrue(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertTrue(response.context['can_delete_task'])
        
        print("\n")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_app/task/table.html')
        
        print("\n")
        
    def test_view_load_fails_when_user_unauthenticated(self):
        """Test that the login page redirects to login view if not logged in."""
        
        print_prologue()
        
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('login')}?next={self.url}", status_code=302, target_status_code=200)
        
        print("\n")
        
    
    
    ##
    #   Testing View pagination
    #
    
    def test_pagination(self):
        """Test that pagination returns the correct page of results."""
        
        print_prologue()
        
        # Create test data with enough items to require multiple pages
        for i in range(25):
            Task.objects.create(type = Task.TaskType.EMPTY)          
        
        response = self.client_normal_user.get(self.url, {'page': 2, 'page_size': 5})
        self.assertEqual(response.status_code, 200)
        # Check that the response contains only the users for page 2
        self.assertEqual(len(response.context['page_obj']), 5)
        
        print("\n")
        

