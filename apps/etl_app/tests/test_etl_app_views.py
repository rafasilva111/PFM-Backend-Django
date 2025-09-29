
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
from apps.etl_app.models import Task
from apps.common.tests.models import BaseViewTestCase


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


###
#
#       Task Views 
#   
##

from apps.etl_app.views import TaskTableView

class TaskTableViewTestCase(BaseViewTestCase):
    
    def setUp(self):
        """Set up a user for testing."""

        super().setUp()
        self.url = reverse('tasks')
        self.template_name = 'etl_app/task/table.html'     
        

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions_for_normal_user(self):
        """Test that a normal user can view tasks but cannot create, edit, or delete tasks."""
        print_prologue()

        # Log in as the normal user
        self.client.force_login(self.normal_user)

        # Use the Django test client to hit the URL
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        self.assertFalse(response.context['can_create_task'])
        self.assertFalse(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertFalse(response.context['can_delete_task'])

        print("\n")

    def test_view_permissions_for_staff_user(self):
        """Test that a staff user can view, edit, and pause tasks but cannot create or delete tasks."""
        
        print_prologue()
            
        # Log in as the normal user
        self.client.force_login(self.staff_user)

        # Use the Django test client to hit the URL
        response = self.client.get(self.url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        self.assertFalse(response.context['can_create_task'])
        self.assertFalse(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertFalse(response.context['can_delete_task'])
        
        print("\n")

    def test_view_permissions_for_super_user(self):
        """Test that a superuser can view, create, edit, and delete tasks."""
        
        print_prologue()
        
        # Log in as the normal user
        self.client.force_login(self.super_user)

        # Use the Django test client to hit the URL
        response = self.client.get(self.url)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        self.assertTrue(response.context['can_create_task'])
        self.assertTrue(response.context['can_edit_task'])
        self.assertTrue(response.context['can_view_task'])
        self.assertTrue(response.context['can_delete_task'])
        
        print("\n")
        
    
    ##
    #   Testing View pagination
    #
    
    def test_pagination(self):
        """Test that pagination returns the correct page of results."""
        
        print_prologue()
        
        # Log in as the normal user
        self.client.force_login(self.super_user)
        
        # Create 25 tasks
        for i in range(25):
            Task.objects.create(type = Task.TaskType.EMPTY)   

        # Use the Django test client to hit the URL
        response = self.client.get(self.url, {'page': 2, 'page_size': 5})
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        self.assertEqual(len(response.context['page_obj']), 5)
        
        print("\n")
        

