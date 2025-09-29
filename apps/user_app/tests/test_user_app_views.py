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

from apps.common.tests.functions import print_prologue
from apps.common.tests.models import BaseViewTestCase


##
#   Contants
#

from apps.common.tests.constants import *


###
#
#       User Invite Views
#
##

class InvidationTestCase(BaseViewTestCase):
        
    def setUp(self):
        super().setUp()

        # Create a test invitation
        self.test_invitation = Invitation.objects.create(
            invited="invite@test.com",
            company=self.test_company,
            inviter=User.objects.get(
                email=f"{TESTING_ACCOUNT_APP_ADMIN}@{TESTING_ACCOUNT_APP_ADMIN}.pt")
        )


class InvitationTableViewTest(InvidationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invites')
        self.template_name = 'user_app/invitation/table.html'

class InvitationDetailViewTest(InvidationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_detail', kwargs={
                           'id': self.test_invitation.id})
        self.template_name = 'user_app/invitation/detail.html'

class InvitationEditViewTest(InvidationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_edit', kwargs={
                           'id': self.test_invitation.id})
        self.template_name = 'user_app/invitation/edit.html'

class InvitationCreateViewTest(InvidationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('user_invite')
        self.template_name = 'user_app/invitation/create.html'

class InvitationSuccessViewTest(InvidationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_success')
        self.template_name = 'common/logged/success_page.html'

###
#
#       User Register Views
#
##


class UserRegisterViewTest(InvidationTestCase):
    """
    Test suite for the user registration view accessed via invitation.

    This class contains tests to ensure that:
    - The registration page for invited users renders correctly.
    - Unauthenticated users are handled appropriately.
    - The correct template is used for rendering the registration page.

    Inheritance:
        InvidationTestCase: Provides setup and utility methods for invitation-based tests.
    """

    def setUp(self):
        """
        Set up the test environment for user registration via invitation.

        Initializes the URL and template name for the registration view using the test invitation token.
        """
        super().setUp()
        self.url = reverse('user_register', kwargs={
                           'token': self.test_invitation.token})
        self.template_name = 'user_app/auth/register_invite.html'

    
    def test_page_renders_correctly_not_authed(self):
        """
        Test that the registration page for invited users renders correctly for unauthenticated users.

        Asserts that the response status code is 200 and the setup is valid.
        """
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        print("\n")

class UserRegisterSuccessViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('user_register_success')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_not_authed(self):
        """
        Test that the registration page for invited users renders correctly for unauthenticated users.

        Asserts that the response status code is 200 and the setup is valid.
        """
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        print("\n")
        
###
#
#       Password Reset Views
#
##

class PasswordResetDoneViewTest(InvidationTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('password_reset_done')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_not_authed(self):
        """Test that the company create page redirects unauthenticated users."""
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        print("\n")
    
class PasswordResetCompleteViewTest(InvidationTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('password_reset_complete')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_not_authed(self):
        """Test that the company create page redirects unauthenticated users."""
        self.assertValidSetup()
        
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        print("\n")
        
###
#
#       User Views
#
##

class UserTableViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('users')
        self.template_name = 'user_app/user/table.html'

class UserDetailViewTest(BaseViewTestCase):
    
    def setUp(self):
        super().setUp()
        user = User.objects.get(
            email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt")
        self.url = reverse('user_detail', kwargs={'id': user.id})
        self.template_name = 'user_app/user/detail.html'

class UserEditViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        user = User.objects.get(
            email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt")
        self.url = reverse('user_edit', kwargs={'id': user.id})
        self.template_name = 'user_app/user/edit.html'


###
#
#       Company Views
#
##

class CompanyTableViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('companies')
        self.template_name = 'user_app/company/table.html'

class CompanyDetailViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_detail', kwargs={
                           'id': self.test_company.id})
        self.template_name = 'user_app/company/detail.html'

class CompanyEditViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_edit', kwargs={'id': self.test_company.id})
        self.template_name = 'user_app/company/edit.html'

class CompanyCreateViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_create')
        self.template_name = 'user_app/company/create.html'
