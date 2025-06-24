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

        # Create a test company
        self.test_company = Company.objects.create(
            name="Test Company",
            email="test@company.com",
            phone="123456789",
            address="Test Address"
        )

        # Create a test invitation
        self.test_invitation = Invitation.objects.create(
            email="invite@test.com",
            company=self.test_company,
            invited_by=User.objects.get(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt")
        )


###
#
#       User Invite Views 
#   
##

class InvitationTableViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invites')
        self.template_name = 'user_app/invitation/table.html'

    def test_page_renders_correctly_authed(self):
        """Test that the invitation table page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the invitation table page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class InvitationDetailViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_detail', kwargs={'id': self.test_invitation.id})
        self.template_name = 'user_app/invitation/detail.html'

    def test_page_renders_correctly_authed(self):
        """Test that the invitation detail page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the invitation detail page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class InvitationEditViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_edit', kwargs={'id': self.test_invitation.id})
        self.template_name = 'user_app/invitation/edit.html'

    def test_page_renders_correctly_authed(self):
        """Test that the invitation edit page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the invitation edit page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class InvitationCreateViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('user_invite')
        self.template_name = 'user_app/invitation/create.html'

    def test_page_renders_correctly_authed(self):
        """Test that the invitation create page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the invitation create page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class InvitationSuccessViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('invite_success')
        self.template_name = 'common/logged/success_page.html'

    def test_page_renders_correctly_authed(self):
        """Test that the invitation success page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the invitation success page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class UserRegisterViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('user_register', kwargs={'token': self.test_invitation.token})
        self.template_name = 'user_app/auth/register_invite.html'

    def test_page_renders_correctly_authed(self):
        """Test that the user register page renders correctly for authenticated users."""
        print_prologue()
        
        # Login as normal user
        self.client.login(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt", password=TESTING_ACCOUNT_C_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the user register page renders correctly for unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")


class UserRegisterSuccessViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('user_register_success')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_authed(self):
        """Test that the user register success page renders correctly for authenticated users."""
        print_prologue()
        
        # Login as normal user
        self.client.login(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt", password=TESTING_ACCOUNT_C_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the user register success page renders correctly for unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")


###
#
#       Password Reset Views 
#   
##

class PasswordResetDoneViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('password_reset_done')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_authed(self):
        """Test that the password reset done page renders correctly for authenticated users."""
        print_prologue()
        
        # Login as normal user
        self.client.login(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt", password=TESTING_ACCOUNT_C_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the password reset done page renders correctly for unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")


class PasswordResetCompleteViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('password_reset_complete')
        self.template_name = 'common/unlogged/success_page.html'

    def test_page_renders_correctly_authed(self):
        """Test that the password reset complete page renders correctly for authenticated users."""
        print_prologue()
        
        # Login as normal user
        self.client.login(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt", password=TESTING_ACCOUNT_C_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the password reset complete page renders correctly for unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")


###
#
#       User Views 
#   
##

class UserTableViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('users')
        self.template_name = 'user_app/user/table.html'

    def test_page_renders_correctly_authed(self):
        """Test that the user table page renders correctly for authenticated users."""
        print_prologue()
        
        # Login as staff user
        self.client.login(email=f"{TESTING_ACCOUNT_B}@{TESTING_ACCOUNT_B}.pt", password=TESTING_ACCOUNT_B_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the user table page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class UserDetailViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        user = User.objects.get(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt")
        self.url = reverse('user_detail', kwargs={'id': user.id})
        self.template_name = 'user_app/user/detail.html'

    def test_page_renders_correctly_authed(self):
        """Test that the user detail page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the user detail page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class UserEditViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        user = User.objects.get(email=f"{TESTING_ACCOUNT_C}@{TESTING_ACCOUNT_C}.pt")
        self.url = reverse('user_edit', kwargs={'id': user.id})
        self.template_name = 'user_app/user/edit.html'

    def test_page_renders_correctly_authed(self):
        """Test that the user edit page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the user edit page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


###
#
#       Company Views 
#   
##

class CompanyTableViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('companies')
        self.template_name = 'user_app/company/table.html'

    def test_page_renders_correctly_authed(self):
        """Test that the company table page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the company table page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class CompanyDetailViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_detail', kwargs={'id': self.test_company.id})
        self.template_name = 'user_app/company/detail.html'

    def test_page_renders_correctly_authed(self):
        """Test that the company detail page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the company detail page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class CompanyEditViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_edit', kwargs={'id': self.test_company.id})
        self.template_name = 'user_app/company/edit.html'

    def test_page_renders_correctly_authed(self):
        """Test that the company edit page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the company edit page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")


class CompanyCreateViewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('company_create')
        self.template_name = 'user_app/company/create.html'

    def test_page_renders_correctly_authed(self):
        """Test that the company create page renders correctly for authenticated users with permissions."""
        print_prologue()
        
        # Login as superuser with permissions
        self.client.login(email=f"{TESTING_ACCOUNT_A}@{TESTING_ACCOUNT_A}.pt", password=TESTING_ACCOUNT_A_PASSWORD)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        
        print("\n")

    def test_page_renders_correctly_not_authed(self):
        """Test that the company create page redirects unauthenticated users."""
        print_prologue()
        
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/auth/login/?next={self.url}")
        
        print("\n")