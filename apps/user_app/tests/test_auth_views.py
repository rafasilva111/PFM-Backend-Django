
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

from apps.common.tests.constants import *


##
#
#       Login Views 
#   
##

USER_EMAIL = "test@example.com"
USER_PASSWORD = "securepassword"
LOGIN_DEFAULT_TEMPLATE = 'user_app/auth/login.html'

class LoginViewTest(TestCase):
    def setUp(self):
        """Set up a user for testing."""
                
        self.user = User.objects.create_user(
            email=USER_EMAIL,
            password=USER_PASSWORD,
            birth_date=timezone.now(),
        )
        self.login_url = reverse('login')  # Assuming the URL name for login is 'login'

    def test_page_renders_correctly(self):
        """Test that the login page renders with correct template and content."""
        
        print_prologue()
        
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, LOGIN_DEFAULT_TEMPLATE)
        self.assertContains(response, "Login")
        
        print("\n")
    
    
    @override_settings(DEBUG=True)  
    def test_login_credentials_None(self):
        """Test that the form shows errors if no credentials are submitted."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': '',
            'password': '',
            'g-recaptcha-response': 'PASSED',  # This is required for ReCaptchaField
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")  # Assuming form validation messages
        self.assertTemplateUsed(response, LOGIN_DEFAULT_TEMPLATE)
        
        print("\n")
    
    @override_settings(DEBUG=True) 
    def test_login_credentials_valid(self):
        """Test that a user can log in with valid credentials."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': USER_EMAIL,
            'password': USER_PASSWORD,
            'remember_me': 'on',
            'g-recaptcha-response': 'PASSED',
        })
        self.assertRedirects(response, reverse('home'))  # Assuming successful login redirects to 'home'
        
        print("\n")
    
    @override_settings(DEBUG=True)  
    def test_login_credentials_invalid(self):
        """Test that invalid login credentials show the proper error."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'wrong@example.com',
            'password': 'wrongpassword',
            'g-recaptcha-response': 'PASSED',  # This is required for ReCaptchaField
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password")
        self.assertTemplateUsed(response, LOGIN_DEFAULT_TEMPLATE)
    
        print("\n")
        
        
    @override_settings(DEBUG=True)
    def test_login_captcha_valid(self):
        """Test login succeeds when valid captcha is provided."""
        print_prologue()
        response = self.client.post(self.login_url, {
            'email': USER_EMAIL,
            'password': USER_PASSWORD,
            'g-recaptcha-response': 'PASSED',  # Simulate valid captcha
        })
        self.assertRedirects(response, reverse('home'))
        print("\n")

    def test_login_captcha_none(self):
        """Test login fails when captcha is missing."""
        print_prologue()
        response = self.client.post(self.login_url, {
            'email': USER_EMAIL,
            'password': USER_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertTemplateUsed(response, LOGIN_DEFAULT_TEMPLATE)
        print("\n")

    
    @override_settings(DEBUG=True)  
    def test_remember_me_valid(self):
        """Test that session expiration is extended when 'remember_me' is checked."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'securepassword',
            'g-recaptcha-response': 'PASSED',  # This is required for ReCaptchaField
            'remember_me': True,
        })
        self.assertRedirects(response, reverse('home'))  # Check if redirected to home after login 
        self.assertTrue(self.client.session.get_expiry_age() > 0)
        
        print("\n")

    @override_settings(DEBUG=True)  
    def test_remember_me_none(self):
        """Test that session expires when 'remember_me' is not checked."""
        
        print_prologue()
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'securepassword',
            'g-recaptcha-response': 'PASSED',  # This is required for ReCaptchaField
        })
        self.assertRedirects(response, reverse('home'))  # Check if redirected to home after login 
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
        