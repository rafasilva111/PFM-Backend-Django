###
#       General imports
##

## 
#   Default
##
import json


##
#   Django
##
from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm,SetPasswordForm,  authenticate, get_user_model, password_validation
from django.utils import timezone
from django.conf import settings
from django.utils.safestring import mark_safe
from apps.common.models import  ProcessType
## 
#   Api Swagger
##


## 
#   Extras
##
from datetime import date,datetime


###
#       App specific imports
##

##
#   Models
#
from apps.user_app.models import User, Group, Invitation, Company

##
#   Contants
#
from apps.user_app.constants import REGISTER_MINIMUM_AGE

from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

###
#
#       Auth Forms 
#   
##
class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.TextInput(attrs={
        'placeholder': 'Enter your email or username',
        'class': 'form-control'
    }))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'placeholder': '********************',
        'class': 'form-control'
    }))
    remember_me = forms.BooleanField(label='Remember Me', required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        " In Debug mode, we will skip the captcha field "
        if settings.DEBUG:
            self.fields['captcha'] = forms.CharField(required=False, widget=forms.HiddenInput())
    
class RegisterForm(UserCreationForm):
    name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Name",
                "class": "form-control"
            }
        ))
    
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    
    
    birth_date = forms.DateField(
        label="Birthdate",
        widget=forms.DateInput(
            attrs={
                "placeholder": "YYYY-MM-DD",
                "class": "form-control",
                "type": "date"  # This adds the date picker
            }
        ))
    
    email = forms.CharField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control"
            }
        ))
    
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))
    
    password2= forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm Password",
                "class": "form-control"
            }
        ))
    

    class Meta:
        model = User
        fields = ['name', 'email','birth_date', 'username', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()

        birth_date = cleaned_data.get("birth_date")
        if birth_date:
            birth_datetime = datetime.combine(birth_date, datetime.min.time())
            # Making birth_date aware
            birth_date_aware = timezone.make_aware(birth_datetime, timezone=timezone.get_current_timezone())
            # Update age in cleaned_data
            age = self.calculate_age(birth_date_aware)
            if age < REGISTER_MINIMUM_AGE:
                self.add_error('birth_date', "You must be at least 18 years old to register.")
    
    def calculate_age(self, birthdate):
        today = today = timezone.now().date()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age

##
#   Password Reset Forms
#

class ResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email',
    }), label="Email Address")

class SetPasswordForm(SetPasswordForm):
    """A custom form for password reset confirmation."""
    
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={'class': 'form-control',"autocomplete": "new-password"}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control',"autocomplete": "new-password"}),
    )
    
    class Meta:
        fields = ('new_password1', 'new_password2')

    
    def clean_confirm_password(self):
        """Ensure that the two password fields match."""
        password = self.cleaned_data.get('new_password1')
        confirm_password = self.cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError(("The two password fields didn’t match."))
        
        return confirm_password

##
#     Invitation Forms
#
    
class InvitationForm(forms.ModelForm):
    
    invited = forms.EmailField(
        label='Email:',
        widget=forms.TextInput(attrs={'class': 'form-control', 'value': '', 'placeholder': 'Enter the invited email'})  # Specify widget here
    )
    
    group = forms.ModelChoiceField(
        label='Group:',
        queryset=Group.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label='Company:',
        required=False,
        disabled=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
    )

    
    class Meta:
        model = Invitation
        fields = ['company','invited','group']
        
        
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        " Initialize the form with the user and company if provided "

            
        " Invited Field"
        self.fields['company'].initial = user.company
        self.fields['company'].disabled = True

        
        " Group field "
        if user.type == user.UserType.APP_ADMIN:
            # Example: Only groups the user belongs to
            self.fields['group'].queryset = Group.objects.filter(name__in=[
                User.UserType.COMPANY_STAFF, User.UserType.COMPANY_ADMIN, User.UserType.APP_STAFF, User.UserType.APP_ADMIN
            ])
            
        elif user.type == user.UserType.COMPANY_ADMIN:
            # Example: Only groups the user belongs to
            self.fields['group'].queryset = Group.objects.filter(name__in=[User.UserType.COMPANY_STAFF, User.UserType.COMPANY_ADMIN])
            
            
            
            
    def clean(self):
        cleaned_data = super().clean()
        
        " Validate email format and uniqueness "
        if User.objects.filter(email=self.cleaned_data['invited']).exists():
            self.add_error('invited', f"This email address ({self.cleaned_data['invited']}) is already in use.")
        
        if Invitation.objects.filter(invited=self.cleaned_data['invited']).exists():
            self.add_error(
                'invited',
                f"This email address ({self.cleaned_data['invited']}) has already been invited. \
                Please ask the recipient to check their inbox or spam folder for the invitation email. \
                If you need to resend the invitation, please do so from the invitation management page."
            )
        
        return cleaned_data
    
    def save(self, user):
        
        instance = super().save(False)
        instance.inviter = user
        instance.company = user.company
        instance.save()
        
        return instance


class InvitationEditForm(forms.ModelForm):
    
    invited = forms.EmailField(
        label='Email:',
        widget=forms.TextInput(attrs={'class': 'form-control', 'value': '', 'placeholder': 'Enter the invited email'})  # Specify widget here
    )
    
    group = forms.ModelChoiceField(
        label='Group:',
        queryset=Group.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label='Company:',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
    )

    
    class Meta:
        model = Invitation
        fields = ['company','invited','group']
        
        
    def __init__(self, user, create= False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        " Group field "
        if user.type == user.UserType.APP_ADMIN:
            # Example: Only groups the user belongs to
            self.fields['group'].queryset = Group.objects.filter(name__in=[
                User.UserType.COMPANY_STAFF, User.UserType.COMPANY_ADMIN, User.UserType.APP_STAFF, User.UserType.APP_ADMIN
            ])
            
        elif user.type == user.UserType.COMPANY_ADMIN:
            # Example: Only groups the user belongs to
            self.fields['group'].queryset = Group.objects.filter(name__in=[User.UserType.COMPANY_STAFF, User.UserType.COMPANY_ADMIN])
            
        
        " Invited  Field"
        self.fields['invited'].disabled = True
            
            
    def clean(self):
        cleaned_data = super().clean()
        
        
        return cleaned_data
    
    def save(self):
        
        instance = super().save(False)
        instance.save()
        
        return instance

class UserRegisterByInviteForm(UserCreationForm):

    
    name = forms.CharField(
        label="Name:",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Name",
                "class": "form-control"
            }
        ))
    
    email = forms.CharField(
        label="Email:",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly"
            }
        ))
    
    sex = forms.ChoiceField(
        label="Sex:",
        choices=User.SexType.choices, 
        help_text='Cron hour field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    password1 = forms.CharField(
        label="Password:",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))
    
    password2= forms.CharField(
        label="Confirm Password:",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm Password",
                "class": "form-control"
            }
        ))
    
    class Meta:
        model = User
        fields = ['name','password1', 'password2', 'email','sex']

    def __init__(self, *args, **kwargs):
        email = kwargs.pop('email', None)
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)


        if email:
            self.fields['email'].initial = email  # Pre-fill email
            
        if company:
            self.fields['company'].initial = company  # Pre-fill email

##
#   User Forms
#

class UserEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['name', 'email','sex', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'sex': forms.Select(choices=User.SexType.choices, attrs={'class': 'form-control'}),
            'type': forms.Select(choices=User.UserType.choices, attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pass the user object to the form
        
        if user is None:
            raise ValueError("User must not be None")
        
        super(UserEditForm, self).__init__(*args, **kwargs)

        # Edit Permissions
        
        if not user.is_staff:
            self.fields['email'].widget.attrs['readonly'] = 'readonly'
            self.fields['type'].widget.attrs['readonly'] = 'readonly'

    def save(self, commit=True):
        # Check if type has changed
        instance = super(UserEditForm, self).save(commit=False)
        
        if self.instance.type != self.cleaned_data['type']:

            # Clear old groups
            instance.groups.clear()

            # Add new groups
            if self.cleaned_data['type'] == User.UserType.NORMAL:
                group = Group.objects.get(name=User.UserType.NORMAL)
                instance.groups.add(group)
            if self.cleaned_data['type'] == User.UserType.STAFF:
                group = Group.objects.get(name=User.UserType.STAFF)
                instance.is_staff = True
                instance.groups.add(group)
            if self.cleaned_data['type'] == User.UserType.SUPERUSER:
                group = Group.objects.get(name=User.UserType.SUPERUSER)
                instance.is_superuser = True    
                instance.groups.add(group)

        if commit:
            instance.save()
        return instance


##
#   Company Forms
#
class CompanyForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Company Name',
            'class': 'form-control'
        })
    )
    processes = forms.MultipleChoiceField(
        choices=ProcessType.choices,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Processes:'
    )
    
    processes.widget.template_name = 'widgets/checkbox_select.html'

    class Meta:
        model = Company
        fields = ['name', 'processes']
