###
#       General imports
##


##
#   Default
#

from django.test import TestCase
from django.contrib.auth.models import Group, Permission
from datetime import datetime

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

from apps.common.models import ProcessType
from apps.user_app.models import User, Company
from apps.recipe_app.models import Recipe, RecipeReport
from apps.etl_app.models import Job, Task, Condition

##
#   Serializers
#


##
#   Forms
#


##
#   Functions
#


##
#   Contants
#

from apps.common.tests.constants import *
from apps.user_app.constants import GROUPS_PERMISSIONS
import random
import string

###
#
#       Functions
#
##


def random_string(length=10):
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choice(characters) for _ in range(length))


def print_prologue():

    print("----------------------------------------------------------------------")
    print("\n")
    print(f"Running test: {inspect.currentframe().f_back.f_code.co_name}")
    print("\n")

##
#   User App
#


def create_test_users(test_case: TestCase, company: Company = None):
    
    # Create predefined users
    for name, is_staff, is_superuser, password, user_type in [
        (TESTING_ACCOUNT_PLACEHOLDER, False, False,
         TESTING_ACCOUNT_PLACEHOLDER_PASSWORD, User.UserType.PLACEHOLDER),
        (TESTING_ACCOUNT_COMPANY, False, False,
         TESTING_ACCOUNT_COMPANY_PASSWORD, User.UserType.COMPANY),
        (TESTING_ACCOUNT_NORMAL, False, False,
         TESTING_ACCOUNT_NORMAL_PASSWORD, User.UserType.NORMAL),
        (TESTING_ACCOUNT_COMPANY_STAFF, True, False,
         TESTING_ACCOUNT_COMPANY_STAFF_PASSWORD, User.UserType.COMPANY_STAFF),
        (TESTING_ACCOUNT_COMPANY_ADMIN, True, False,
         TESTING_ACCOUNT_COMPANY_ADMIN_PASSWORD, User.UserType.COMPANY_ADMIN),
        (TESTING_ACCOUNT_APP_STAFF, True, False,
         TESTING_ACCOUNT_APP_STAFF_PASSWORD, User.UserType.APP_STAFF),
        (TESTING_ACCOUNT_APP_ADMIN, True, True,
         TESTING_ACCOUNT_APP_ADMIN_PASSWORD, User.UserType.APP_ADMIN),
    ]:
        user, created = User.objects.get_or_create(
            name=name,
            email=f"{name}@{name}.pt",
            is_staff=is_staff,
            is_superuser=is_superuser,
            type=user_type,
            company=company
        )

        if created:
            user.set_password(password)
            user.save()

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

    # Create clients for each user type
    test_case.placeholder_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_PLACEHOLDER}@{TESTING_ACCOUNT_PLACEHOLDER}.pt")
    test_case.company_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_COMPANY}@{TESTING_ACCOUNT_COMPANY}.pt")
    test_case.normal_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_NORMAL}@{TESTING_ACCOUNT_NORMAL}.pt")
    test_case.company_staff_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_COMPANY_STAFF}@{TESTING_ACCOUNT_COMPANY_STAFF}.pt")
    test_case.company_admin_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_COMPANY_ADMIN}@{TESTING_ACCOUNT_COMPANY_ADMIN}.pt")
    test_case.app_staff_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_APP_STAFF}@{TESTING_ACCOUNT_APP_STAFF}.pt")
    test_case.app_admin_user = User.objects.get(
        email=f"{TESTING_ACCOUNT_APP_ADMIN}@{TESTING_ACCOUNT_APP_ADMIN}.pt")

    return test_case


def create_test_company(name: str = None):

    # Create a test company
    return Company.objects.create(
        name=name if name else random_string(6)
    )

##
#   Recipe App
#


def create_test_recipe(company: Company = None, user: User = None):

    return Recipe.objects.create(
        title=random_string(6),
        description=random_string(12),
        created_by=user,
        company=company
    )


def create_test_recipe_report(recipe: Recipe = None, user: User = None):

    return RecipeReport.objects.create(
        title=random_string(6),
        message=random_string(12),
        recipe=recipe,
        user=user
    )

##
#   ETL App
#


def create_test_task(type: Job.TaskType, process: ProcessType, company: Company, user: User, starting_condition: Condition = None, stopping_condition: Condition = None, parent_job: Job = None):

    extract_job = Job.objects.create(
        type=type,
        process=process,
        name=f'Test Extract Job {datetime.now().timestamp()}',
        company=company,
        created_by=user,
        parent_job=parent_job,
        starting_condition=starting_condition,
        stopping_condition=stopping_condition
    )

    extract_task = Task.objects.create(
        type=type,
        process=process,
        company=company,
        owner_job=extract_job,
        debug_mode=True
    )

    return extract_job, extract_task
