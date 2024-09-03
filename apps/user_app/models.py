from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.forms import TextInput, PasswordInput
from django.db import models
from datetime import datetime
from django.utils import timezone
from django.utils.translation import  gettext_lazy
from apps.common.models import BaseModel




class Company(BaseModel):
    name = models.CharField(max_length=255, null=False, unique=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True)

    imgs_bucket = models.CharField(max_length=255, null=False)

    user_account = models.OneToOneField('User',related_name="main_company", on_delete=models.CASCADE, default=None, null=True) 

    def __str__(self):
        return f"{self.id} - {self.name}"


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
    
        
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            password=password,
            username=username,
            birth_date = datetime(2000, 3, 15)
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

class FloatChoices(models.TextChoices):
    @classmethod
    def values(cls):
        return [choice[0] for choice in cls.choices]

    @classmethod
    def labels(cls):
        return [choice[1] for choice in cls.choices]
        

class User(AbstractBaseUser):

    name = models.CharField(max_length=40, null=False)
    username = models.CharField(max_length=255, null=False, unique=True)
    description = models.CharField(max_length=255, default='',blank=True)
    birth_date = models.DateTimeField(null=False)
    img_source = models.CharField(max_length=255, default='',blank=True)
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

    
    follows_c = models.IntegerField(default=0)
    followers_c = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()

    @property
    def age(self):
        today = timezone.now()
        age = today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
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
    

    company = models.ForeignKey(Company, related_name='user', on_delete=models.CASCADE, null=True, blank=True)

    
    class UserType(models.TextChoices):
        NORMAL = 'N', 'Normal'
        COMPANY = 'C', 'Company'
        PREMIUM = 'P', 'Premium'
        ADMIN = 'A', 'Admin'

    user_type = models.CharField(
        max_length=1,
        choices=UserType.choices,
        default=UserType.NORMAL,
        null=False
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
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        try:
            self.age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        except:
            pass
    
        super().save(*args, **kwargs)  # Call the original save() method
    
class MyModelQuerySet(models.QuerySet):
    def delete(self):
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

class FollowRequest(BaseModel):
    follower = models.ForeignKey(User, related_name='followers_request', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followeds_request', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Follow(BaseModel):
    follower = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    followed = models.ForeignKey(User, related_name='followeds', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
