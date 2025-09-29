import pytest
from django.urls import reverse
from django.test import Client
from django.http import HttpResponseServerError
from apps.common.tests.functions import create_test_users
from django.test import TestCase, override_settings
from django.urls import path, reverse
import types

@pytest.fixture
def client():
    return Client()

class PageErrorTests(TestCase):
    
    def setUp(self):
        self.url = "/does-not-exist/"
        self.template_name = 'recipe_app/audit_log/detail.html'
        
        create_test_users(self)
        
    @override_settings(DEBUG=False)
    def test_403_forbidden(self):
        
        # Log in as the Placeholder user
        self.client.force_login(self.placeholder_user)
        
        # Perform the action
        response = self.client.get("/tasks")
        
        # Check Response
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'common/page_error.html')
    
    @override_settings(DEBUG=False)
    def test_404_not_found(self):
        
        # Perform the action
        response = self.client.get(self.url)
        
        # Check Response
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'common/page_error.html')
        

