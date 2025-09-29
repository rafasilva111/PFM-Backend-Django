# Django imports
from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
    Permission,
    Group,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import send_mail

# Third-party imports
from multiselectfield import MultiSelectField
import random

# Local imports
from apps.common.models import BaseModel, ProcessType
from apps.common.constants import INVITATION_EMAIL_SUBJECT

# Standard library imports
import uuid

##
#   Logging
#

import logging
logger = logging.getLogger(__name__)


##
#   Company
#

class Company(BaseModel):
    """
    Company model that represents a company entity.

    Attributes:
        name (str): The name of the company. This field is required and must be unique.
        email (str): The email address of the company. This field is required and must be unique.
        imgs_bucket (str): The bucket name where the company's images are stored. This field is required.
        user_account (User): A one-to-one relationship with the User model, representing the user account associated with the company. This field is optional and can be null.

    Methods:
        __str__(): Returns a string representation of the company, including its ID and name.
    """
    name = models.CharField(max_length=255, null=False, unique=True)
    
    imgs_bucket = models.CharField(max_length=255, null=False)

    user_account = models.OneToOneField('User',related_name="company_owner", on_delete=models.CASCADE, default=None, null=True) 

    processes = MultiSelectField(
        choices=ProcessType.choices,
        max_length=40,  # Adjust based on expected selections
        default=list
    )

    def __str__(self):
        return f"{self.id} - {self.name}"
    
    class Meta:
        permissions = [
            ("can_view_company", "Can view Company's details"),
            ("can_view_companies", "Can view Companies list"),
            ("can_create_company", "Can resend a Company"),
            ("can_edit_company", "Can edit a Company"),
            ("can_delete_company", "Can delete a Company"),
        ]

##
#   User
#

class UserManager(BaseUserManager):
    """
    Custom manager for handling user creation with email as the unique identifier
    instead of a username. This manager provides methods for creating regular users
    and superusers, with automatic group assignment to new users.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and returns a new user with the given email and password, and assigns
        the user to a default group. Raises a ValueError if the email is not provided.

        Args:
            email (str): The user's email address, used as a unique identifier.
            password (str): The user's password.
            **extra_fields: Additional fields to set on the user model.

        Returns:
            User: The created user instance.

        Raises:
            ValueError: If the email is not provided.
        """

        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and returns a new superuser with the given email and password,
        setting is_staff and is_superuser to True. If these values are not True,
        a ValueError is raised.

        Args:
            email (str): The superuser's email address, used as a unique identifier.
            password (str): The superuser's password.
            **extra_fields: Additional fields to set on the user model.

        Returns:
            User: The created superuser instance.

        Raises:
            ValueError: If is_staff or is_superuser are not True.
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        # Use create_user to create the superuser and assign any additional roles
        user = self.create_user(email, password, **extra_fields)

        return user

class User(AbstractBaseUser, PermissionsMixin):
    """
    User model that extends AbstractBaseUser and PermissionsMixin.
    """

    name = models.CharField(max_length=40, null=False)
    username = models.CharField(max_length=255, null=False)
    image = models.CharField(max_length=255, default=f"avatar{random.randint(1, 10)}.png", blank=True)
    email = models.EmailField(verbose_name="email address", max_length=255, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Security
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    security_group = models.ManyToManyField(Group, related_name="users", blank=True)
    user_permissions = models.ManyToManyField(
        Permission, related_name="user_set", blank=True
    )

    objects = UserManager()
    
    description = models.CharField(max_length=255, default='',blank=True)
    birth_date = models.DateTimeField(null=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True)
    user_portion = models.IntegerField(default=-1)
    is_active = models.BooleanField(default=True)
    fmc_token = models.CharField(max_length=255, default='',blank=True)
    height = models.FloatField(default=-1)
    weight = models.FloatField(default=-1)
    is_admin = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    company = models.ForeignKey(Company, related_name='users', on_delete=models.CASCADE, null=True, blank=True)
    
    follows_c = models.IntegerField(default=0)
    followers_c = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()

    @property
    def age(self):
        today = timezone.now()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return age
    
    class ActivityLevel(models.TextChoices):
        NOTHING = "1", gettext_lazy('Nothing')
        SEDENTARY = "1.2" , gettext_lazy('Sedentary')
        LIGHT = "1.375", gettext_lazy('Light')
        MODERATE = "1.465", gettext_lazy('Moderate')  
        ACTIVE = "1.55", gettext_lazy('Active')  
        VERY_ACTIVE = "1.725", gettext_lazy('Very Active')
        EXTRA_ACTIVE = "1.9" , gettext_lazy('Extra Active')  
        
    activity_level = models.CharField(
        max_length=5,
        choices=ActivityLevel.choices,
        default=ActivityLevel.NOTHING 
    )
    
    class ProfileType(models.TextChoices):
        PROTECT = 'PROTECT', gettext_lazy('Protect')
        PRIVATE = 'PRIVATE', gettext_lazy('Private')
        PUBLIC = 'PUBLIC', gettext_lazy('Public')  
        
    profile_type = models.CharField(
        max_length=10,
        choices=ProfileType.choices,
        default=ProfileType.PRIVATE
    )
    

    class UserType(models.TextChoices):
        PLACEHOLDER = "Placeholder", "Placeholder"
        COMPANY = "Company", "Company"
        NORMAL = "Normal", "Normal"
        APP_STAFF = "Application Staff", "Application Staff"
        APP_ADMIN = "Application Admin", "Application Admin"
        COMPANY_STAFF = "Company Staff", "Company Staff"
        COMPANY_ADMIN = "Company Admin", "Company Admin"

    type = models.CharField(
        choices=UserType.choices, default=UserType.NORMAL, null=False
    )
    
    class SexType(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'

    sex = models.CharField(
        max_length=1,
        choices=SexType.choices,
        default=None,
        null=True
    )
   
    USERNAME_FIELD = 'email'

    class Meta:
        permissions = [
            ("can_view_user", "Can view User's details"),
            ("can_view_users", "Can view Users list"),
            ("can_invite_user", "Can invite a User"),
            ("can_edit_user", "Can edit a User"),
            ("can_delete_user", "Can delete a User"),
            ("can_enable_user", "Can Enable a User"),
            ("can_disable_user", "Can Disable a User"),
        ]

    USERNAME_FIELD = "email"

    def __str__(self):
        return f"{self.id} - {self.name}"

##
#   Auth
#   
        
class Invitation(BaseModel):
    """
    Invitation model represents an invitation sent to a user via email.

    Attributes:
        email (EmailField): The email address to which the invitation is sent.
        token (UUIDField): A unique token for the invitation, generated by default.
        created_at (DateTimeField): The date and time when the invitation was created.

    Methods:
        __str__(): Returns a string representation of the invitation.
    """
    
    invited = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="invitations")
    inviter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="invitations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite to {self.invited}"

    
    class Meta:
        permissions = [
            ("can_view_invite", "Can view Invite's details"),
            ("can_view_invites", "Can view Invites list"),
            ("can_resend_invite", "Can resend a Invite"),
            ("can_edit_invite", "Can edit a Invite"),
            ("can_delete_invite", "Can delete a Invite"),
        ]
    
    def send_invitation_email(self, invitation):
        
        success = True
        
        invite_link = f'{settings.BASE_URL}{reverse("user_register", args=[invitation.token])}'  # Tokenized link

        # Render the email template
        message = render_to_string('user_app/auth/emails/invite_email.html', {
            'invite_link': invite_link,
            'sender_email':invitation.inviter.email,
            'sender_name': invitation.inviter.name,
        })

        # Send the email
        try:
            sent_count = send_mail(
                INVITATION_EMAIL_SUBJECT,
                message,
                settings.DEFAULT_FROM_EMAIL,  # From email
                [invitation.invited],  # To email
                fail_silently=False,
            )
            
            
            if sent_count > 0:
                logger.info("Email sent successfully to %s.", invitation.invited)
            else:
                logger.warning("Invitation email was not sent to %s.", invitation.invited)
                success = False
                
        except Exception as e:
            logger.error("Error sending invitation email to %s: %s", invitation.invited, e)
            success = False
            
            
        return success

##
#   Goal
#

class Goal(BaseModel):
    goal = models.FloatField()
    calories = models.FloatField()
    fat_upper_limit = models.FloatField()
    fat_lower_limit = models.FloatField()
    saturated_fat = models.FloatField()
    carbohydrates = models.FloatField()
    proteins_upper_limit = models.FloatField()
    proteins_lower_limit = models.FloatField()
    user = models.ForeignKey(User, related_name='goals', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        super(Goal, self).delete(using, keep_parents)

##
#   Follows
#

class FollowRequest(BaseModel):
    follower = models.ForeignKey(User, related_name='followers_request', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followeds_request', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Follow(BaseModel):
    follower = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followeds', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)