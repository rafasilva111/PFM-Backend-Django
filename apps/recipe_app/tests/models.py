
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

from apps.common.tests.functions import print_prologue, create_test_recipe, create_test_recipe_report, create_test_audit_log
from apps.common.tests.models import _BaseViewTestCase, _BaseViewFunctionTestCase


##
#   Contants
#

from apps.common.tests.constants import *




##
#      TestCases
#

##
#   Recipe 
#

def recipe_view_test_setup(self, user: User):
    self.recipe = create_test_recipe(user = user, company=self.company)

class _RecipeViewTestCase(_BaseViewTestCase):
         
     def setUp(self):
          super().setUp()
          recipe_view_test_setup(self, self.app_admin_user)

class _RecipeViewFunctionTestCase(_BaseViewFunctionTestCase):
         
     def setUp(self):
          super().setUp()
          recipe_view_test_setup(self, self.app_admin_user)


##
#   Audit Log
#

def audit_log_view_test_setup(self):
    self.recipe = create_test_recipe()
    self.task = Task.objects.create(type=Task.TaskType.EMPTY)
    self.audit_log = create_test_audit_log(self.recipe, self.task)

class _AuditLogViewTestCase(_BaseViewTestCase):
    
        
    def setUp(self):
        super().setUp()
        audit_log_view_test_setup(self)
        
class _AuditLogViewFunctionTestCase(_BaseViewFunctionTestCase):
        
    def setUp(self):
        super().setUp()
        audit_log_view_test_setup(self)


##
#   Recipe Report
#

def recipe_report_view_test_setup(self):
    self.recipe = create_test_recipe()
    self.recipe_report = create_test_recipe_report(self.recipe, self.app_admin_user)

class _RecipeReportViewTestCase(_BaseViewTestCase):
        
    def setUp(self):
        super().setUp()
        recipe_report_view_test_setup(self)

class _RecipeReportViewFunctionTestCase(_BaseViewFunctionTestCase):
        
    def setUp(self):
        super().setUp()
        recipe_report_view_test_setup(self)