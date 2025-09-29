###
#       General imports
##


##
#   Default
#

from django.urls import reverse
from urllib.parse import urlencode

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

from apps.recipe_app.models import RecipeAuditLog, Recipe, RecipeAuditLogStatusHistory
from apps.etl_app.models import Task

##
#   Serializers
#


##
#   Forms
#


##
#   Functions
#

from apps.common.tests.functions import print_prologue, create_test_recipe, create_test_recipe_report
from apps.common.tests.models import BaseViewTestCase, BaseViewFunctionTestCase


##
#   Contants
#

from apps.common.tests.constants import *


###
#
#       Recipe Views
#
##

##
#      Tests
#

class RecipeTableViewTest(BaseViewTestCase):
    
    url = reverse('recipes')
    template_name = 'recipe_app/recipe/table.html'
    permission = "can_view_recipe_reports"
    buttons = [DROPDOWN_DETAILS_BUTTON_ID, DROPDOWN_DELETE_BUTTON_ID]
    
    def setUp(self):
        
        super().setUp()
        self.recipe = create_test_recipe()
     
    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 200, True),
            (self.company_staff_user, 200, True),
            (self.company_admin_user, 200, True),
            (self.app_staff_user, 200, True),
            (self.app_admin_user, 200, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
        
    def test_buttons_permissions(self):
        """Test that the dropdown menu shows correct options based on user permissions."""
        
        print_prologue()
               
        # Create another test recipe report to ensure multiple entries for off and on class atribute testing
        company_staff_user_recipe = create_test_recipe(self.company, self.company_staff_user)

        
        # Create another test recipe report to ensure multiple entries for off and on class atribute testing
        company_admin_user_recipe = create_test_recipe(self.company, self.company_admin_user)
        
        
        # Define test cases with expected options
        test_cases = [
            (self.placeholder_user, {}),
            (self.company_user, {}),
            (self.normal_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe"
            }),
            (self.company_staff_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe"
            }),
            (self.company_admin_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe"
            }),
            (self.app_staff_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe"
            }),
            (self.app_admin_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe",
            DROPDOWN_DELETE_BUTTON_ID: "can_delete_recipe"
            }),
        ]
        
        # Iterate through test cases
        for user, expected_options in test_cases:
            
            self.client.force_login(user)
            response = self.client.get(self.url)
            
            # Check if the user has the required permission
            if user.has_perm(self.permission_):
                self.assertEqual(response.status_code, 200)
            else:
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 403)
                continue
            
            # Check the dropdown button options
            self.check_user_button_permission(expected_options, response)
        
    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test that the recipe table view loads correctly."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.app_admin_user)
        
        # Access the recipe table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that the correct template was used
        self.assertTemplateUsed(response, self.template_name)
        
        # Check that the recipe is in the context
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.recipe)
        
    

class RecipeDetailViewTest(BaseViewTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('recipe_detail')
        self.template_name = 'recipe_app/recipe/detail.html'
        
class RecipeDeleteViewFunctionTest(BaseViewFunctionTestCase):
    
    permission = "can_delete_recipe"
    
    def setUp(self):
        super().setUp()
        create_test_recipe(self)
        self.url = reverse('recipe_delete', kwargs={'id': self.recipe.id})
        
        
    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        
        print_prologue()
        
        # Recreate the recipe for each test case since deletion will remove it
        #create_test_recipe(self)
        
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 403, False),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
            print(f"Testing how many recipes exits {Recipe.objects.all().count()}")
            #create_test_recipe(self)  # Recreate the recipe after each deletion test
    
    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test deleting a recipe."""
        
        print_prologue()
        
        # Ensure the audit log exists before deletion
        self.assertTrue(Recipe.objects.filter(id=self.recipe.id).exists())
        
        # Log in as the normal user
        self.client.force_login(self.app_admin_user)
        
        # Perform the delete action
        response = self.client.get(self.url)
        
        # Check for a redirect after deletion
        self.assertEqual(response.status_code, 302)
        
        # Ensure the audit log no longer exists
        self.assertFalse(Recipe.objects.filter(id=self.recipe.id).exists())
        
    
    

###
#
#       Audit Log Views
#
##


##
#      Setup function
#

def create_audit_log_setup(self):
    # Create a test Recipe
    self.recipe = create_test_recipe(self.company, self.company_admin_user)
    
    # Create a test Task
    self.task = Task.objects.create(
        type = Task.TaskType.EMPTY
    )

    # Create a test invitation
    return RecipeAuditLog.objects.create(
        recipe = self.recipe,
        task = self.task,
        description="This is a test audit log.",
        field="name",
        old_value="Old Recipe Name",
        new_value="New Recipe Name",
        type=RecipeAuditLog.Type.Create
        
    )
    

##
#      TestCases
#

class AuditLogTestCase(BaseViewTestCase):
        
    def setUp(self):
        super().setUp()
        self.audit_log = create_audit_log_setup(self)
        
class AuditLogFunctionTestCase(BaseViewFunctionTestCase):
        
    def setUp(self):
        super().setUp()
        create_audit_log_setup(self)
   

##
#      Tests
#

class AuditLogTableViewTest(AuditLogTestCase):
    
    url = reverse('audit_logs')
    template_name = 'recipe_app/audit_log/table.html'
    permission = "can_view_audit_logs"
    buttons = [DROPDOWN_DETAILS_BUTTON_ID, DROPDOWN_DELETE_BUTTON_ID]
    
    def setUp(self):
        super().setUp()

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 200, True),
            (self.app_staff_user, 200, True),
            (self.app_admin_user, 200, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
        

    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test that the recipe table view loads correctly."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.app_admin_user)
        
        # Access the recipe table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that the correct template was used
        self.assertTemplateUsed(response, self.template_name)
        
        # Check that the recipe is in the context
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.audit_log)
    
    ##
    #   Testing Granularly View Functionality
    #
    
    def test_buttons_permissions(self):
        """Test that the dropdown menu shows correct options based on user permissions."""
        
        print_prologue()
        
        # Ensure a test audit log exists
        self.assertIsNotNone(self.audit_log)
        
        # Create another test audit log to ensure multiple entries for off and on class atribute testing
        second_audit_log = RecipeAuditLog.objects.create(
            recipe = self.recipe,
            task = self.task,
            description="This is a second test audit log.",
            field="description")
        second_audit_log.accept(changed_by=self.app_admin_user)
        second_audit_log.review(changed_by=self.app_admin_user)
        
        # Define test cases with expected options
        test_cases = [
            (self.placeholder_user, {}),
            (self.company_user, {}),
            (self.normal_user, {}),
            (self.company_staff_user, {}),
            (self.company_admin_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_audit_log"
            }),
            (self.app_staff_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_audit_log",
            DROPWON_ACCEPT_BUTTON_ID: "can_accept_audit_log",
            DROPWON_UNACCEPT_BUTTON_ID: "can_unaccept_audit_log",
            DROPWON_REVIEW_BUTTON_ID: "can_review_audit_log",
            DROPWON_UNREVIEW_BUTTON_ID: "can_unreview_audit_log"
            }),
            (self.app_admin_user, {
            DROPDOWN_DETAILS_BUTTON_ID: "can_view_audit_log",
            DROPWON_ACCEPT_BUTTON_ID: "can_accept_audit_log",
            DROPWON_UNACCEPT_BUTTON_ID: "can_unaccept_audit_log",
            DROPWON_REVIEW_BUTTON_ID: "can_review_audit_log",
            DROPWON_UNREVIEW_BUTTON_ID: "can_unreview_audit_log",
            DROPDOWN_DELETE_BUTTON_ID: "can_delete_audit_log"
            }),
        ]
        
        # Iterate through test cases
        for user, expected_options in test_cases:
            
            self.client.force_login(user)
            response = self.client.get(self.url)
            
            # Check if the user has the required permission
            if user.has_perm(self.permission_):
                self.assertEqual(response.status_code, 200, f"User {user.email} expected 200 but got {response.status_code}")
            else:
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 403, f"User {user.email} expected 403 but got {response.status_code}")
                continue
            
            # Check the dropdown button options
            self.check_user_button_permission(expected_options, response)
        
class AuditLogDetailViewTest(AuditLogTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_detail', kwargs={'id': self.audit_log.id})
        self.template_name = 'recipe_app/audit_log/detail.html'


       
class AuditLogDeleteViewFunctionTest(AuditLogFunctionTestCase):
    
    permission = "can_delete_audit_log"
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_delete', kwargs={'id': self.audit_log.id})
    
    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 403, False),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)

    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test deleting an audit log."""
        
        # Ensure the audit log exists before deletion
        self.assertTrue(RecipeAuditLog.objects.filter(id=self.audit_log.id).exists())
        
        # Log in as the normal user
        self.client.force_login(self.app_admin_user)
        
        # Perform the delete action
        response = self.client.get(self.url)
        
        # Check for a redirect after deletion
        self.assertEqual(response.status_code, 302)
        
        # Ensure the audit log no longer exists
        self.assertFalse(RecipeAuditLog.objects.filter(id=self.audit_log.id).exists())
    
    
class AuditLogAcceptViewFunctionTest(AuditLogFunctionTestCase):
    
    permission = "can_accept_audit_log"
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_accept', kwargs={'id': self.audit_log.id})        
        
        
    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
            
    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test accepting an audit log."""
        
        # Ensure the audit log is initially not accepted
        self.assertFalse(self.audit_log.accepted)
        
        # Log in as the normal user
        self.client.force_login(self.app_admin_user)
        
        # Perform the accept action
        response = self.client.get(self.url)
        
        # Check for a redirect after accepting
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.audit_log.refresh_from_db()
        self.recipe.refresh_from_db()
        
        # Ensure the audit log is now accepted
        self.assertTrue(self.audit_log.accepted)

        # Ensure recipe is verified after accepting the audit log
        self.assertTrue(self.recipe.verified)
        
        # Ensure Recipe Audit change was logged on RecipeAuditLogStatusHistory
        history_entries = self.audit_log.status_history.all()
        self.assertEqual(history_entries.count(), 2)
        self.assertEqual(history_entries.first().status, RecipeAuditLogStatusHistory.Status.Reviewed)
        self.assertEqual(history_entries.last().status, RecipeAuditLogStatusHistory.Status.Accepted)
    
    ##
    #   Testing Granularly View Functionality
    #
    
    def test_only_verfied_after_all_audit_logs_accepted(self):
        """Test that the recipe is only verified after all audit logs are accepted."""
        
        # Create a second audit log for the same recipe
        second_audit_log = RecipeAuditLog.objects.create(
            recipe=self.recipe,
            task=self.task,
            description="This is a second test audit log.",
            field="description",
            old_value="Old Description",
            new_value="New Description",
            type=RecipeAuditLog.Type.Update
        )
        
        # Ensure both audit logs are initially not accepted
        self.assertFalse(self.audit_log.accepted)
        self.assertFalse(second_audit_log.accepted)
        
        # Log in as the app admin user
        self.client.force_login(self.app_admin_user)
        
        # Accept the first audit log
        response = self.client.get(reverse('audit_log_accept', kwargs={'id': self.audit_log.id}))
        self.assertEqual(response.status_code, 302)
        
        # Refresh both audit logs from the database
        self.audit_log.refresh_from_db()
        second_audit_log.refresh_from_db()
        
        # Ensure the first audit log is accepted and the second is not
        self.assertTrue(self.audit_log.accepted)
        self.assertFalse(second_audit_log.accepted)
        
        # Ensure the recipe is still not verified
        self.recipe.refresh_from_db()
        self.assertFalse(self.recipe.verified)
        
        # Accept the second audit log
        response = self.client.get(reverse('audit_log_accept', kwargs={'id': second_audit_log.id}))
        self.assertEqual(response.status_code, 302)
        
        # Refresh both audit logs and the recipe from the database
        self.audit_log.refresh_from_db()
        second_audit_log.refresh_from_db()
        self.recipe.refresh_from_db()
        
        # Ensure both audit logs are accepted
        self.assertTrue(self.audit_log.accepted)
        self.assertTrue(second_audit_log.accepted)
        
        # Ensure the recipe is now verified
        self.assertTrue(self.recipe.verified)   

class AuditLogUnacceptViewFunctionTest(AuditLogFunctionTestCase):
    
    permission = "can_unaccept_audit_log"
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_unaccept', kwargs={'id': self.audit_log.id})        
        
        
    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
            
    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test accepting an audit log."""
        
        # First, ensure the audit log is accepted to set it up for unaccepting
        self.audit_log.accepted = True
        self.audit_log.reviewed = True
        self.audit_log.save(self.app_admin_user)
        
        # Ensure the audit log is initially accepted
        self.assertTrue(self.audit_log.accepted)
        
        # Log in as the normal user
        self.client.force_login(self.app_admin_user)
        
        # Perform the accept action
        response = self.client.get(self.url)
        
        # Check for a redirect after unaccepting
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.audit_log.refresh_from_db()
        self.recipe.refresh_from_db()
        
        # Ensure the audit log is now unaccepted
        self.assertFalse(self.audit_log.accepted)

        # Ensure recipe is verified after accepting the audit log
        self.assertFalse(self.recipe.verified)
        
        # Ensure Recipe Audit change was logged on RecipeAuditLogStatusHistory
        history_entries = self.audit_log.status_history.all()
        self.assertEqual(history_entries.count(), 4)
        self.assertEqual(history_entries[0].status, RecipeAuditLogStatusHistory.Status.Reviewed)
        self.assertEqual(history_entries[1].status, RecipeAuditLogStatusHistory.Status.Accepted)
        self.assertEqual(history_entries[2].status, RecipeAuditLogStatusHistory.Status.Unreviewed)
        self.assertEqual(history_entries[3].status, RecipeAuditLogStatusHistory.Status.Unaccepted)
    

class AuditLogReviewViewFunctionTest(AuditLogFunctionTestCase):
    
    permission = "can_review_audit_log"
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_review', kwargs={'id': self.audit_log.id})

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
    
    ##
    #   Testing General View Functionality
    #    
    
    def test_functionality(self):
        """Test reviewing an audit log."""
        
        # Ensure the audit log is initially not reviewed
        self.assertFalse(self.audit_log.reviewed)
        
        # Log in as the app staff user
        self.client.force_login(self.app_admin_user)
        
        # Perform the review action
        response = self.client.get(self.url)
        
        # Check for a redirect after reviewing
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.audit_log.refresh_from_db()
        
        # Ensure the audit log is now reviewed
        self.assertTrue(self.audit_log.reviewed)
        
        # Ensure Recipe Audit change was logged on RecipeAuditLogStatusHistory
        history_entries = self.audit_log.status_history.all()
        self.assertEqual(history_entries.count(), 1)
        self.assertEqual(history_entries.first().status, RecipeAuditLogStatusHistory.Status.Reviewed)

class AuditLogUnreviewViewFunctionTest(AuditLogFunctionTestCase):
    
    permission = "can_unreview_audit_log"
    
    def setUp(self):
        super().setUp()
        self.url = reverse('audit_log_unreview', kwargs={'id': self.audit_log.id})

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
    
    ##
    #   Testing General View Functionality
    #    
    
    def test_functionality(self):
        """Test unreviewing an audit log."""
        
        # First, ensure the audit log is reviewed to set it up for unreviewing
        self.audit_log.reviewed = True
        self.audit_log.save(self.app_admin_user)
        
        # Ensure the audit log is initially reviewed
        self.assertTrue(self.audit_log.reviewed)
        
        # Log in as the app staff user
        self.client.force_login(self.app_staff_user)
        
        # Perform the unreview action
        response = self.client.get(self.url)
        
        # Check for a redirect after unreviewing
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.audit_log.refresh_from_db()
        
        # Ensure the audit log is now unreviewed
        self.assertFalse(self.audit_log.reviewed)
        
        # Ensure Recipe Audit change was logged on RecipeAuditLogStatusHistory
        history_entries = self.audit_log.status_history.all()
        self.assertEqual(history_entries.count(), 2)
        self.assertEqual(history_entries[0].status, RecipeAuditLogStatusHistory.Status.Reviewed)
        self.assertEqual(history_entries[1].status, RecipeAuditLogStatusHistory.Status.Unreviewed)
        
    
###
#
#       Recipe Report Views
#
##

class RecipeReportFunctionTestCase(BaseViewTestCase):
        
    def setUp(self):
        super().setUp()
        self.recipe = create_test_recipe()
        self.recipe_report = create_test_recipe_report(self.recipe, self.app_admin_user)
   


class RecipeReportTableViewTest(RecipeReportFunctionTestCase):
    
    url = reverse('recipe_reports')
    template_name = 'recipe_app/report/table.html'
    permission = "can_view_recipe_reports"
    buttons = [DROPDOWN_DETAILS_BUTTON_ID, DROPDOWN_DELETE_BUTTON_ID, DROPWON_REVIEW_BUTTON_ID, DROPWON_UNREVIEW_BUTTON_ID]
    
    def setUp(self):
        super().setUp()

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 200, True),
            (self.company_staff_user, 200, True),
            (self.company_admin_user, 200, True),
            (self.app_staff_user, 200, True),
            (self.app_admin_user, 200, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
    
    def test_normal_user_permissions(self):
        """Test that a normal user cannot view the recipe reports."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.normal_user)
        
        # Create a test recipe report
        create_test_recipe_report(self.recipe, self.normal_user)
        
        # Access the recipe report table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check if User has permission to only view his own recipe reports
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)  # Normal user should
        
    def test_company_staff_user_permissions(self):
        """Test that a company user cannot view the recipe reports."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.company_staff_user)
        
        # Create a test recipe report
        recipe = create_test_recipe(self.company, self.company_staff_user)
        create_test_recipe_report(recipe, self.company_staff_user)
        
        # Assert the recipe report was created
        self.assertIsNotNone(self.recipe_report)
        
        # Access the recipe report table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check if User has permission to only view his own recipe reports
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)  # Company user should not see any recipe reports

    def test_company_admin_user_permissions(self):
        """Test that a company admin user cannot view the recipe reports."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.company_admin_user)
        
        # Create a test recipe report
        recipe = create_test_recipe(self.company, self.company_admin_user)
        create_test_recipe_report(recipe, self.company_admin_user)
        
        # Access the recipe report table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check if User has permission to only view his own recipe reports
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)  # Company user should not see any recipe reports
    
    ##
    #   Testing General View Functionality
    #
    
    def test_functionality(self):
        """Test that the recipe table view loads correctly."""
        
        print_prologue()
        
        # Log in as a user with permission to view recipes
        self.client.force_login(self.app_admin_user)
        
        # Access the recipe report table view
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that the correct template was used
        self.assertTemplateUsed(response, self.template_name)
        
        # Check that the recipe is in the context
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.recipe_report)
    
    ##
    #   Testing Granularly View Functionality
    #
    
    def test_buttons_permissions(self):
        """Test that the dropdown menu shows correct options based on user permissions."""
        
        print_prologue()
        
        # Ensure a test recipe report exists
        self.assertIsNotNone(self.recipe_report)
        
        # As this users have different permissions on different recipe reports, we need to create multiple reports
        # Create another test recipe report to ensure multiple entries for off and on class atribute testing
        normal_user_first_instance = create_test_recipe_report(self.recipe, self.normal_user)
        normal_user_second_instance = create_test_recipe_report(self.recipe, self.normal_user)
        normal_user_second_instance.review(reviewed_by=self.app_admin_user)
        
        # Create another test recipe report to ensure multiple entries for off and on class atribute testing
        company_staff_user_recipe = create_test_recipe(self.company, self.company_staff_user)
        company_staff_user_first_instance = create_test_recipe_report(company_staff_user_recipe, self.company_staff_user)
        company_staff_user_second_instance = create_test_recipe_report(company_staff_user_recipe, self.company_staff_user)
        company_staff_user_second_instance.review(reviewed_by=self.app_admin_user)
        
        # Create another test recipe report to ensure multiple entries for off and on class atribute testing
        company_admin_user_recipe = create_test_recipe(self.company, self.company_admin_user)
        acompany_admin_user_first_instance = create_test_recipe_report(company_admin_user_recipe, self.company_admin_user)
        company_admin_user_second_instance = create_test_recipe_report(company_admin_user_recipe, self.company_admin_user)
        company_admin_user_second_instance.review(reviewed_by=self.app_admin_user)
        
        
        # Define test cases with expected options
        test_cases = [
            (self.placeholder_user, {}),
            (self.company_user, {}),
            (self.normal_user, {
                DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe_report"
            }),
            (self.company_staff_user, {
                DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe_report"
            }),
            (self.company_admin_user, {
                DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe_report"
            }),
            (self.app_staff_user, {
                DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe_report",
                DROPWON_REVIEW_BUTTON_ID: "can_review_recipe_report",
                DROPWON_UNREVIEW_BUTTON_ID: "can_unreview_recipe_report"
            }),
            (self.app_admin_user, {
                DROPDOWN_DETAILS_BUTTON_ID: "can_view_recipe_report",
                DROPWON_REVIEW_BUTTON_ID: "can_review_recipe_report",
                DROPWON_UNREVIEW_BUTTON_ID: "can_unreview_recipe_report",
                DROPDOWN_DELETE_BUTTON_ID: "can_delete_recipe_report"
            }),
        ]
        
        # Iterate through test cases
        for user, expected_options in test_cases:
            
            self.client.force_login(user)
            response = self.client.get(self.url)
            
            # Check if the user has the required permission
            if user.has_perm(self.permission_):
                self.assertEqual(response.status_code, 200, f"User {user.email} expected 200 but got {response.status_code}")
            else:
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 403, f"User {user.email} expected 403 but got {response.status_code}")
                continue
            
            # Check the dropdown button options
            self.check_user_button_permission(expected_options, response)
      

class RecipeReportCreateViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('recipe_report_create')
        self.template_name = 'recipe_app/recipe_report/create.html'

class RecipeReportDetailViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.report_id = 1
        self.url = reverse('recipe_report_detail', kwargs={'id': self.report_id})
        self.template_name = 'recipe_app/recipe_report/detail.html'
        

class RecipeReportReviewViewFunctionTest(BaseViewFunctionTestCase):
    
    permission = "can_review_recipe_report"
    
    def setUp(self):
        super().setUp()
        self.recipe = create_test_recipe(self.company, self.company_admin_user)
        self.recipe_report = create_test_recipe_report(self.recipe, self.app_admin_user)
        self.url = reverse('recipe_report_review', kwargs={'id': self.recipe_report.id})
        

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
    
    ##
    #   Testing General View Functionality
    #    
    
    def test_functionality(self):
        """Test reviewing an audit log."""
        
        # Ensure the audit log is initially not reviewed
        self.assertFalse(self.recipe_report.reviewed)
        
        # Log in as the app staff user
        self.client.force_login(self.app_admin_user)
                
        # Perform the review action
        response = self.client.get(self.url)
        
        # Check for a redirect after reviewing
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.recipe_report.refresh_from_db()
        
        # Ensure the audit log is now reviewed
        self.assertTrue(self.recipe_report.reviewed)
        

class RecipeReportUnreviewViewFunctionTest(BaseViewFunctionTestCase):
    
    permission = "can_unreview_recipe_report"
    
    def setUp(self):
        super().setUp()
        self.recipe = create_test_recipe(self.company, self.company_admin_user)
        self.recipe_report = create_test_recipe_report(self.recipe, self.app_admin_user)
        self.url = reverse('recipe_report_unreview', kwargs={'id': self.recipe_report.id})

    ##
    #   Testing View permissions
    #
    
    def test_view_permissions(self):
        """Test permissions for various user roles."""
        test_cases = [
            (self.placeholder_user, 403, False),
            (self.company_user, 403, False),
            (self.normal_user, 403, False),
            (self.company_staff_user, 403, False),
            (self.company_admin_user, 403, False),
            (self.app_staff_user, 302, True),
            (self.app_admin_user, 302, True),
        ]
        for user, expected_status, should_have_permission in test_cases:
            self.check_user_permission_and_response(user, expected_status, should_have_permission=should_have_permission)
    
    ##
    #   Testing General View Functionality
    #    
    
    def test_functionality(self):
        """Test unreviewing an audit log."""
        
        # First, ensure the audit log is reviewed to set it up for unreviewing
        self.recipe_report.reviewed_by = self.app_admin_user
        self.recipe_report.save()
        
        # Ensure the audit log is initially reviewed
        self.assertTrue(self.recipe_report.reviewed)
        
        # Log in as the app staff user
        self.client.force_login(self.app_admin_user)
        
        # Perform the unreview action
        response = self.client.get(self.url)
        
        # Check for a redirect after unreviewing
        self.assertEqual(response.status_code, 302)
        
        # Refresh the audit log from the database
        self.recipe_report.refresh_from_db()
        
        # Ensure the audit log is now unreviewed
        self.assertFalse(self.recipe_report.reviewed)
        
  