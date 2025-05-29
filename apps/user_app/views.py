###
#       General imports
##


##
#   Default
#

from web_project import TemplateLayout

##
#   Django 
#
from django.shortcuts import render,redirect,get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.views.decorators.http import require_GET, require_POST
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from django.views.generic import TemplateView
import markdown
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect
from django.utils.http import  urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy

from django.contrib.auth import login as auth_login
from django.contrib.auth.views import PasswordResetConfirmView as BasePasswordResetConfirmView,PasswordResetView ,PasswordContextMixin,INTERNAL_RESET_SESSION_TOKEN
import logging

##
#   Api Swagger
#


##
#   Extras
#
from web_project import TemplateLayout, TemplateHelper



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
from apps.user_app.forms import LoginForm, RegisterForm, ResetForm, SetPasswordForm, InvitationForm, InvitationEditForm, \
                            UserRegisterByInviteForm, UserEditForm, CompanyForm

##
#   Filters
#

from apps.user_app.filters import UserFilter, InvitationFilter, CompanyFilter


##
#   Functions
#


##
#   Contants
#

from apps.common.constants import INVITATION_EMAIL_SUBJECT

##
#   Logging
#

logger = logging.getLogger(__name__)

###
#
#       Auth Views 
#   
##

class LoginView(TemplateView):
    """
    View for handling user login.
    Attributes:
        template_name (str): Path to the login template.
        form_class (LoginForm): Form class for login.
    Methods:
        get_context_data(**kwargs):
            Adds additional context data to the template context.
        post(request):
            Handles POST requests for user login. Authenticates the user and logs them in if credentials are valid.
            Sets session expiry based on the 'remember_me' option.
    """
    template_name = 'user_app/auth/login.html'
    form_class = LoginForm

    def get_context_data(self, **kwargs):
        
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        context.update({
            'layout_path' : TemplateHelper.set_layout("layout_blank.html", context),
            'form': self.form_class(),
        })
        return context

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        
        context = self.get_context_data()
        
        return render(request, self.template_name, context)

    def post(self, request):
        """
        Handle POST requests for user login.
        This method processes the login form, authenticates the user, and manages session expiry based on the 'remember me' option.
        Args:
            request (HttpRequest): The HTTP request object containing POST data.
        Returns:
            HttpResponse: Redirects to the next URL or home page if authentication is successful.
                          Renders the login template with form errors if authentication fails or form is invalid.
        """
        instance_form = self.form_class(request.POST)
        if instance_form.is_valid():
            email = instance_form.cleaned_data['email']
            password = instance_form.cleaned_data['password']
            remember_me  = instance_form.cleaned_data['remember_me']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)

                if remember_me:
                    # If remember_me is checked, set a longer session expiry time
                    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                else:
                    # If remember_me is not checked, use the default session expiry time
                    request.session.set_expiry(0)  # Expire at browser close
                
                # Redirect to the next URL or home page after successful login
                next_url = request.GET.get('next', reverse('home'))
                return redirect(next_url)
            else:
                # Add an error to the form if authentication fails
                instance_form.add_error("password", "Invalid email or password")
                
        # If form is invalid or authentication failed, pass form with errors back to template
        context = self.get_context_data()
        context['form'] = instance_form
        
        return render(request, self.template_name, context)

class RegisterView(View):
    """
    View for handling user registration.

    Methods:
        get(request): Handles GET requests and displays the registration form.
        post(request): Handles POST requests, validates the form, creates a new user, and redirects to the login page on success.

    Attributes:
        form (RegisterForm): The registration form instance.
    """
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        """
        Handle POST request for user registration.

        This method processes the registration form submitted by the user. It validates the form data,
        attempts to create a new user, and handles any exceptions that may occur during the user creation process.

        Args:
            request (HttpRequest): The HTTP request object containing the form data.

        Returns:
            HttpResponse: A redirect to the login page with a success message if the user is registered successfully.
                          Otherwise, it renders the registration page with the form and any error messages.
        """
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            try:
                user = form.save()
                return redirect('login', {"msg": "User registered successfully, please login"})
            except Exception as e:
                error_message = str(e)
                if "EMAIL_EXISTS" in error_message:
                    form.add_error("email", "Email already exists.")
                else:
                    form.add_error("password2", error_message)
        return render(request, 'accounts/register.html', {'form': form})

class LogoutView(LoginRequiredMixin,PasswordContextMixin,View):
    """
    LogoutView handles the user logout process.

    This view requires the user to be logged in and provides the necessary context for password management.

    Methods:
        post(request): Logs out the user and redirects to the login page.

    Attributes:
        LoginRequiredMixin: Ensures that the user is logged in to access this view.
        PasswordContextMixin: Provides context for password management.
        View: Inherits from Django's base View class.
    """

    def post(self, request):
        logout(request)

        return redirect('login')

###
#
#       User Invite Views 
#   
##

@method_decorator(login_required, name='dispatch')
class InvitationTableView(PermissionRequiredMixin, TemplateView):
    """
    View to display the user invitation table.
    This view extends `PermissionRequiredMixin` and `TemplateView` to ensure
    that only users with the required permissions can access it. It renders
    a table of user invitations with pagination and filtering capabilities.
    Attributes:
        template_name (str): The path to the template used to render the invitation table.
        permission_required (str): The permission required to access this view.
    Methods:
        get_context_data(**kwargs):
            Adds the invitation table data to the context.
    """
    template_name = 'user_app/invitation/table.html'
    permission_required = 'user_app.can_view_invites'
    page_size = 10
    
    def get_context_data(self, **kwargs):
        return TemplateLayout.init(self, super().get_context_data(**kwargs))
    
    def get(self, request, *args, **kwargs):

        # Initialize template layout
        context = self.get_context_data()
        
        # Retrieve and order all users
        records = Invitation.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = InvitationFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
    
        # Implement pagination
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        # Created context
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_invite": self.request.user.has_perm(
                    "user_app.can_view_invite"
                ),
                "can_invite_user": self.request.user.has_perm(
                    "user_app.can_invite_user"
                ),
                "can_edit_invite": self.request.user.has_perm(
                    "user_app.can_edit_invite"
                ),
                "can_delete_invite": self.request.user.has_perm(
                    "user_app.can_delete_invite"
                ),
            }
        )
        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class InvitationDetailView(PermissionRequiredMixin, TemplateView):
    """
    View to display the details of a user.
    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.
    Attributes:
        template_name (str): The path to the template used to render the view.
        permission_required (str): The permission required to access this view.
    Methods:
        get_context_data(**kwargs): Adds user details to the context.
    """
    template_name = 'user_app/invitation/detail.html'
    permission_required = 'user_app.can_view_invite'
    
    def get_context_data(self, **kwargs):
        
        return TemplateLayout.init(self, super().get_context_data(**kwargs))
    
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to display the invitation details.
        Retrieves the invitation object based on the provided ID and adds it to the context.
        
        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Rendered template with the invitation details.
        """
        context = self.get_context_data(**kwargs)
        
        # Retrieve Instances
        instance = Invitation.objects.get(id=kwargs["id"])
        
        # Create context
        context.update({
            "instance": instance,
            "can_resend_invite": self.request.user.has_perm(
                "user_app.can_resend_invite"
            ),
            "can_edit_invite": self.request.user.has_perm(
                "user_app.can_edit_invite"
            ),
            "can_delete_invite": self.request.user.has_perm(
                "user_app.can_delete_invite"
            ),
        })
        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class InvitationEditView(PermissionRequiredMixin, TemplateView):
    """
    View for editing a user.

    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.

    Attributes:
        template_name (str): The path to the template used for rendering the view.
        permission_required (str): The permission required to access this view.
        form_class (UserEditForm): The form class used for editing the user.

    Methods:
        get_object(): Retrieves the User object or raises a 404 error.
        get_context_data(**kwargs): Adds the UserEditForm to the context.
        post(request, *args, **kwargs): Handles form submission for editing a user.


        Returns:
            User: The user object retrieved by ID.


        Args:
            **kwargs: Additional context data.

        Returns:
            dict: The context data including the form.


        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
    """
    template_name = 'user_app/invitation/edit.html'
    permission_required = 'user_app.can_edit_invite'
    form_class = InvitationEditForm

    
    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Adds job form and time condition forms to context.
    
        Returns:
            dict: Context dictionary containing:
                - form: JobForm instance.
                - starting_condition_time_form: TimeConditionForm instance for starting condition.
                - stopping_condition_time_form: TimeConditionForm instance for stopping condition.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        return context

    def get(self, request, *args, **kwargs):
        
        # Obtain the context
        context = self.get_context_data(**kwargs)
        
        # Retrieve Instances
        instance = Invitation.objects.get(id=kwargs["id"])
        
        # Create context
        context.update({
            "form": self.form_class(
                instance=instance,
                user=request.user
            ),
        })
        
        return self.render_to_response(context)
        
    def post(self, request, *args, **kwargs):
        """
        Handles form submission for creating a new job.
        - Validates and saves the job form and time condition forms.
        - Redirects to job detail view on success, or re-renders form with errors.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to job detail view on success.
            HttpResponse: Re-renders form with errors on failure.
        """
        
        # Retrieve Instances
        instance = Invitation.objects.get(id=kwargs["id"])
        
        # Create job form
        instance_form = self.form_class(
            instance=instance,
            user=request.user,
            data=request.POST            
        )
        
        # Validate Job form
        if instance_form.is_valid():

            # Save the Job
            instance = instance_form.save()
            
            return redirect(reverse("invite_detail", args=[instance.id]))
        
        # Create context
        context = self.get_context_data()
        context.update(
            {
                "form": instance_form
            }
        )        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class InvitationView(PermissionRequiredMixin,TemplateView):
    """
    View to handle user invitations.
    This view allows users with the appropriate permissions to invite new users to the application by sending them an email with an invitation link.
    Attributes:
        template_name (str): The path to the template used to render the invitation form.
        permission_required (str): The permission required to access this view.
        form_class (InvitationForm): The form class used to handle user invitations.
    Methods:
        get_context_data(**kwargs):
            Adds the invitation form to the context data.
        post(request, *args, **kwargs):
            Handles the form submission, validates the form, creates an invitation, and sends an invitation email.
        send_invitation_email(invitation, request):
            Sends an email with the invitation link to the invited user.
    """
    template_name = 'user_app/invitation/create.html'
    permission_required = 'auth.add_user'
    form_class = InvitationForm
    
    def get_context_data(self, **kwargs):
        return TemplateLayout.init(self, super().get_context_data(**kwargs))

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to render the invitation form.
        This method initializes the context with the invitation form and returns the rendered template.
        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        Returns:
            HttpResponse: Rendered template with the invitation form.
        """
        context = self.get_context_data()
        context['form'] = self.form_class(
            user = request.user
        )
        return self.render_to_response(context)
        
    def post(self, request, *args, **kwargs):
        
        instance_form = self.form_class(
            user=request.user,
            data=request.POST
        ) 
        
        if instance_form.is_valid():
            
            " Create Invitation "
            instance = instance_form.save(request.user)

            " Send tokenized invite email "
            success = instance.send_invitation_email(instance)
            
            if success:
                return redirect('invite_success')
            
            messages.error(request, 'Failed to send invitation email. Please try again later.')
            instance.delete()
            
        
        # Collect all errors if any form is invalid
        context = self.get_context_data()
        context['form'] = instance_form
        
        return self.render_to_response(context)
    
    
        
@method_decorator(login_required, name='dispatch')
class InvitationSuccessView(PermissionRequiredMixin, TemplateView):
    """
    View to display a success message after a user invitation is sent.
    This view extends `PermissionRequiredMixin` and `TemplateView` to ensure
    that only users with the required permissions can access it. It renders
    a success page with a custom message and a link to redirect back to the
    user table.
    Attributes:
        template_name (str): The path to the template used to render the success page.
    Methods:
        get_context_data(**kwargs): Adds additional context data to the template.
    """
    permission_required = 'auth.add_user'
    template_name = 'common/logged/success_page.html'
    
    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            'title': 'Success!',
            'message': 'Invitation sent successfully!',
            'tab': 'User / Invite User /',
            'current_tab': 'Success',
            'redirect_url': reverse('invites'),
            'redirect_text': 'Back to User Table'
        })
        return context

class UserRegisterView(TemplateView):
    """
    View for handling user registration via invitation.
    Attributes:
        template_name (str): Path to the template used for rendering the view.
        form_class (Form): Form class used for user registration.
    Methods:
        get_context_data(**kwargs):
            Retrieves and updates the context data for the view.
            Raises:
                SuspiciousOperation: If the token is not provided or invalid.
        post(request, *args, **kwargs):
            Handles the POST request to register a user.
            Returns:
                HttpResponse: Redirects to the success page if the form is valid,
                              otherwise re-renders the form with errors.
    """
    template_name = 'user_app/auth/invite_register.html'
    form_class = UserRegisterByInviteForm
    
    def get_context_data(self, **kwargs):
        """
        Override the get_context_data method to provide additional context data for the template.
        This method initializes the context using the TemplateLayout and sets the layout path.
        It retrieves the 'token' from the URL kwargs and uses it to fetch the corresponding Invitation object.
        If the token is not provided or invalid, a SuspiciousOperation exception is raised.
        If the invitation exists, it pre-fills the form with the invitation's email and company.
        Args:
            **kwargs: Arbitrary keyword arguments passed to the method.
        Returns:
            dict: The context dictionary with additional data for the template.
        Raises:
            SuspiciousOperation: If the token is not provided or invalid.
        """
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path']  = TemplateHelper.set_layout("layout_blank.html", context)
        
        token = self.kwargs.get('token', None)
        
        if not token:
            raise SuspiciousOperation("Token not provided")
        
        # Get Invitation
        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            
            # Check if user is already registered
            try:
                user = User.objects.get(email=invitation.email)
                # todo: User is already registered. Show message and redirect to login
                
            except User.DoesNotExist:
                raise SuspiciousOperation("Token is Invalid")
            
        form = self.form_class(email=invitation.email,company=invitation.company)
        context['form'] = form

        return context

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for user registration.
        This method processes the form data submitted via a POST request. If the form is valid,
        it saves the form data, prints the URL for the user registration success page, and redirects
        the user to that page. If the form is not valid, it re-renders the form with error messages.
        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        Returns:
            HttpResponse: A redirect to the user registration success page if the form is valid,
                          otherwise the rendered form with error messages.
        """
        instance_form = self.form_class(request.POST)
        
        if instance_form.is_valid():
            
            instance_form.save()
            print(reverse('user_register_success'))
            return redirect(reverse('user_register_success'))

        context = self.get_context_data()
        context['form'] = instance_form
        
        return self.render_to_response(context)

class UserRegisterSuccessView(TemplateView):
    """
    UserRegisterSuccessView is a Django TemplateView that renders a success page 
    after a user successfully registers.
    Attributes:
        template_name (str): The path to the template used to render the success page.
    Methods:
        get_context_data(**kwargs):
            Adds additional context data to the template, including layout path, 
            title, success message, and redirect URL.
    """
    template_name = 'common/unlogged/success_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'layout_path': TemplateHelper.set_layout("layout_blank.html", context),
            'title': 'Success!',
            'message': 'Your account is created successfully!',
            'redirect_url': reverse('login')
        })
        return context


###
#   Actions
#


@login_required
@require_GET
@permission_required('user_app.can_delete_user', raise_exception=True)
def invite_delete(request, id):
    
    instance = get_object_or_404(Invitation, id=id)
    instance.delete()
    
    return redirect("invites")

@login_required
@require_GET
@permission_required('user_app.can_resend_email', raise_exception=True)
def invite_resend(request, id):
    """
    Resend an invitation email to the user.
    
    This function retrieves the invitation by its ID, sends the invitation email,
    and redirects back to the previous page with a success message.
    
    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the invitation to resend.
        
    Returns:
        HttpResponseRedirect: Redirects back to the previous page with a success message.
    """
    instance = get_object_or_404(Invitation, id=id)
    
    # Send the invitation email
    success = instance.send_invitation_email()
    
    if success:
        messages.success(request, "Invitation email resent successfully.")
    else:
        messages.error(request, "Failed to resend invitation email. Please try again later.")
    
    return redirect(request.META.get('HTTP_REFERER', '/'))



###
#
#       Password Reset Views 
#   
##


class PasswordResetView(PasswordResetView):
    template_name = 'common/auth/reset_password/password_reset.html'  # Assuming your template path
    form_class = ResetForm
    success_url = reverse_lazy('password_reset_done')

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path'] = TemplateHelper.set_layout("layout_blank.html", context)
        context['form'] = self.form_class()

        return context

    def post(self, request, *args, **kwargs):
        self.form = self.form_class(request.POST)

        if self.form.is_valid():
            return super().post(request, *args, **kwargs)  # Let the default password reset logic run

        # If form is invalid, return the form with errors
        context = self.get_context_data(form=self.form)
        return render(request, self.template_name, context)

class PasswordResetDoneView(TemplateView):
    template_name = "common/unlogged/success_page.html"
    # Predefined function
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path'] = TemplateHelper.set_layout("layout_blank.html", context)
        context['title'] = 'Reset your password'
        context['message'] = 'We’ve emailed you instructions for setting your password, if an account exists with the email you entered. You should receive them shortly.'
        context['redirect_url'] = reverse('login')
        context['redirect_text'] = 'Back to Login'
        return context     

class PasswordResetConfirmView(PasswordContextMixin, FormView):
    form_class = SetPasswordForm
    post_reset_login = False
    post_reset_login_backend = None
    reset_url_token = "set-password"
    success_url = reverse_lazy("password_reset_complete")
    template_name = "common/auth/reset_password/password_reset_confirm.html"
    title = _("Enter new password")
    token_generator = default_token_generator

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        self.validlink = False
        self.user = self.get_user(kwargs["uidb64"])

        if self.user is not None:
            token = kwargs["token"]
            session_token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)

            # Check the token validity
            if self.token_generator.check_token(self.user, session_token):
                self.validlink = True
                return super().dispatch(*args, **kwargs)
            elif self.token_generator.check_token(self.user, token):
                self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
                redirect_url = self.request.path.replace(token, self.reset_url_token)
                return HttpResponseRedirect(redirect_url)

        # Render failure response
        return self.render_to_response(self.get_context_data())
    
    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User._default_manager.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            ValidationError,
        ):
            user = None
        return user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
        if self.post_reset_login:
            auth_login(self.request, user, self.post_reset_login_backend)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path'] = TemplateHelper.set_layout("layout_blank.html", context)
        
        if self.validlink:
            context["validlink"] = True
        else:
            context.update(
                {
                    "form": None,
                    "title": _("Password reset unsuccessful"),
                    "validlink": False,
                }                
            )
        return context

class PasswordResetCompleteView(TemplateView):
    """
    View for displaying a success message after a password reset is complete.
    """
    template_name = "common/unlogged/success_page.html"

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Sets the title, message, and redirect information.

        Returns:
            dict: Context containing:
                - layout_path: Path to the layout template.
                - title: Title of the success message.
                - message: Success message content.
                - redirect_url: URL to redirect after displaying the message.
                - redirect_text: Text for the redirect link.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Update context with title, message, and redirect information
        context.update({
            'layout_path': TemplateHelper.set_layout("layout_blank.html", context),
            'title': 'Password set!',
            'message': 'Your password has been reset. You can log in now.',
            'redirect_url': reverse('login'),
            'redirect_text': 'Back to Login'
        })
        
        return context


###
#
#       User Views 
#   
##


@method_decorator(login_required, name='dispatch')
class UserTableView(LoginRequiredMixin, TemplateView):
    """
    A view class that displays a paginated table of users with filtering capabilities.
    This view requires user authentication and specific permission to view users.
    It extends TemplateView and implements LoginRequiredMixin for access control.

    Attributes:
        template_name (str): Path to the template used to render the user table.
        page_size (int): Default number of items per page.
        permission_required (str): Permission required to access this view.

    Methods:
        get_context_data(**kwargs): Prepares and returns the context data for template rendering.
            - Initializes template layout.
            - Retrieves and orders all users.
            - Applies filtering based on request parameters.
            - Implements pagination.
            - Adds user permissions to the context.
    """

    template_name = 'user_app/user/table.html'
    permission_required = "user_app.can_view_users"
    page_size = 10

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Retrieves and orders all users.
        - Applies filtering based on request parameters.
        - Implements pagination.
        - Adds user permissions to the context.

        Returns:
            dict: Context containing:
                - filter: Filtered queryset of users.
                - page_obj: Paginator object with user records.
                - can_view_user: Boolean indicating if user can view users.
                - can_invite_user: Boolean indicating if user can invite users.
                - can_edit_user: Boolean indicating if user can edit users.
                - can_disable_user: Boolean indicating if user can disable users.
                - can_delete_user: Boolean indicating if user can delete users.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve and order all users
        records = User.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = UserFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
    
        # Implement pagination
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        # Created context
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_user": self.request.user.has_perm(
                    "user_app.can_view_user"
                ),
                "can_invite_user": self.request.user.has_perm(
                    "user_app.can_invite_user"
                ),
                "can_edit_user": self.request.user.has_perm(
                    "user_app.can_edit_user"
                ),
                "can_enable_user": self.request.user.has_perm(
                    "user_app.can_enable_user"
                ),
                "can_disable_user": self.request.user.has_perm(
                    "user_app.can_disable_user"
                ),
                "can_delete_user": self.request.user.has_perm(
                    "user_app.can_delete_user"
                ),
            }
        )
        
        return context

@method_decorator(login_required, name='dispatch')
class UserDetailView(PermissionRequiredMixin, TemplateView):
    """
    View to display the details of a user.
    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.
    Attributes:
        template_name (str): The path to the template used to render the view.
        permission_required (str): The permission required to access this view.
    Methods:
        get_context_data(**kwargs): Adds user details to the context.
    """
    template_name = 'user_app/user/detail.html'
    permission_required = 'user_app.can_view_user'
    
    def get_context_data(self, **kwargs):
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['record'] = User.objects.get(id=kwargs['id'])           
        
        return context

@method_decorator(login_required, name='dispatch')
class UserEditView(PermissionRequiredMixin, TemplateView):
    """
    View for editing a user.

    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.

    Attributes:
        template_name (str): The path to the template used for rendering the view.
        permission_required (str): The permission required to access this view.
        form_class (UserEditForm): The form class used for editing the user.

    Methods:
        get_object(): Retrieves the User object or raises a 404 error.
        get_context_data(**kwargs): Adds the UserEditForm to the context.
        post(request, *args, **kwargs): Handles form submission for editing a user.


        Returns:
            User: The user object retrieved by ID.


        Args:
            **kwargs: Additional context data.

        Returns:
            dict: The context data including the form.


        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
    """
    template_name = 'user_app/user/edit.html'
    permission_required = 'auth.change_user'
    form_class = UserEditForm

    def get_object(self):
        """
        Retrieve the User object or raise a 404 error.
        """
        instance_id = self.kwargs.get('id')
        return get_object_or_404(User, id=instance_id)

    def get_context_data(self, **kwargs):
        """
        Add the UserEditForm to the context.
        """
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['form'] = self.form_class(instance=self.get_object(), user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle form submission for editing a user.
        """
        user = self.get_object()
        form = self.form_class(request.POST, instance=user, user=request.user)

        if form.is_valid():
            form.save()
            return redirect(reverse("user_detail", args=[user.id]))

        # Re-render the form with errors
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


###
#   Actions
#


@login_required
@require_GET
@permission_required('user_app.can_enable_user', raise_exception=True)
def user_enable(request, id):
    instance = get_object_or_404(User, id=id)
    instance.is_active = True
    instance.save()
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_GET
@permission_required('user_app.can_disable_user', raise_exception=True)
def user_disable(request, id):
    instance = get_object_or_404(User, id=id)
    instance.is_active = False
    instance.save()
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
@require_GET
@permission_required('user_app.can_delete_user', raise_exception=True)
def user_delete(request, id):
    instance = get_object_or_404(User, id=id)
    instance.delete()
    
    return redirect("users")


###
#
#       Company Views 
#   
##


@method_decorator(login_required, name='dispatch')
class CompanyTableView(PermissionRequiredMixin, TemplateView):
    """
    View to display the user invitation table.
    This view extends `PermissionRequiredMixin` and `TemplateView` to ensure
    that only users with the required permissions can access it. It renders
    a table of user invitations with pagination and filtering capabilities.
    Attributes:
        template_name (str): The path to the template used to render the invitation table.
        permission_required (str): The permission required to access this view.
    Methods:
        get_context_data(**kwargs):
            Adds the invitation table data to the context.
    """
    template_name = 'user_app/company/table.html'
    permission_required = 'user_app.can_view_companies'
    page_size = 10
    
    def get_context_data(self, **kwargs):
        return TemplateLayout.init(self, super().get_context_data(**kwargs))
    
    def get(self, request, *args, **kwargs):

        # Initialize template layout
        context = self.get_context_data()
        
        # Retrieve and order all users
        records = Company.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = CompanyFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
    
        # Implement pagination
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        # Created context
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_company": self.request.user.has_perm(
                    "user_app.can_view_company"
                ),
                "can_create_company": self.request.user.has_perm(
                    "user_app.can_create_company"
                ),
                "can_edit_company": self.request.user.has_perm(
                    "user_app.can_edit_company"
                ),
                "can_delete_company": self.request.user.has_perm(
                    "user_app.can_delete_company"
                ),
            }
        )
        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class CompanyDetailView(PermissionRequiredMixin, TemplateView):
    """
    View to display the details of a user.
    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.
    Attributes:
        template_name (str): The path to the template used to render the view.
        permission_required (str): The permission required to access this view.
    Methods:
        get_context_data(**kwargs): Adds user details to the context.
    """
    template_name = 'user_app/company/detail.html'
    permission_required = 'user_app.can_view_company'
    page_size = 10
    
    def get_context_data(self, **kwargs):
        
        return TemplateLayout.init(self, super().get_context_data(**kwargs))
    
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to display the invitation details.
        Retrieves the invitation object based on the provided ID and adds it to the context.
        
        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Rendered template with the invitation details.
        """
        context = self.get_context_data(**kwargs)
        
        # Retrieve Instances
        instance = Company.objects.get(id=kwargs["id"])
        
        # Apply filtering based on request parameters
        users_filter = UserFilter(self.request.GET, queryset=instance.users.all())
        users_filtered_records = users_filter.qs
    
        # Implement pagination
        paginator = Paginator(
            users_filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        
        # Create context
        context.update({
            "instance": instance,
            "can_edit_company": self.request.user.has_perm(
                "user_app.can_edit_company"
            ),
            "can_delete_company": self.request.user.has_perm(
                "user_app.can_delete_company"
            ),
            "filter": users_filter,
            "total_count": paginator.count,
            "page_obj": page_obj,
            "can_view_user": self.request.user.has_perm(
                "user_app.can_view_user"
            ),
            "can_edit_user": self.request.user.has_perm(
                "user_app.can_edit_user"
            ),
            "can_enable_user": self.request.user.has_perm(
                "user_app.can_enable_user"
            ),
            "can_disable_user": self.request.user.has_perm(
                "user_app.can_disable_user"
            ),
            "can_delete_user": self.request.user.has_perm(
                "user_app.can_delete_user"
            ),
        })
        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class CompanyEditView(PermissionRequiredMixin, TemplateView):
    """
    View for editing a user.

    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.

    Attributes:
        template_name (str): The path to the template used for rendering the view.
        permission_required (str): The permission required to access this view.
        form_class (UserEditForm): The form class used for editing the user.

    Methods:
        get_object(): Retrieves the User object or raises a 404 error.
        get_context_data(**kwargs): Adds the UserEditForm to the context.
        post(request, *args, **kwargs): Handles form submission for editing a user.


        Returns:
            User: The user object retrieved by ID.


        Args:
            **kwargs: Additional context data.

        Returns:
            dict: The context data including the form.


        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
    """
    template_name = 'user_app/company/edit.html'
    permission_required = 'user_app.can_edit_invite'
    form_class = CompanyForm

    
    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Adds job form and time condition forms to context.
    
        Returns:
            dict: Context dictionary containing:
                - form: JobForm instance.
                - starting_condition_time_form: TimeConditionForm instance for starting condition.
                - stopping_condition_time_form: TimeConditionForm instance for stopping condition.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        return context

    def get(self, request, *args, **kwargs):
        
        # Obtain the context
        context = self.get_context_data(**kwargs)
        
        # Retrieve Instances
        instance = Company.objects.get(id=kwargs["id"])
        
        # Create context
        context.update({
            "form": self.form_class(
                instance=instance
            ),
        })
        
        return self.render_to_response(context)
        
    def post(self, request, *args, **kwargs):
        """
        Handles form submission for creating a new job.
        - Validates and saves the job form and time condition forms.
        - Redirects to job detail view on success, or re-renders form with errors.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to job detail view on success.
            HttpResponse: Re-renders form with errors on failure.
        """
        
        " Retrieve Instances "
        instance = Company.objects.get(id=kwargs["id"])
        
        " Create Instance form "
        instance_form = self.form_class(
            instance=instance,
            data=request.POST            
        )
        
        " Validate Instance form "
        if instance_form.is_valid():

            " Save Instance Job "
            instance = instance_form.save()
            
            return redirect(reverse("company_detail", args=[instance.id]))
        
        " Create context "
        context = self.get_context_data()
        context.update(
            {
                "form": instance_form
            }
        )
        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class CompanyCreateView(PermissionRequiredMixin,TemplateView):
    """
    View to handle user invitations.
    This view allows users with the appropriate permissions to invite new users to the application by sending them an email with an invitation link.
    Attributes:
        template_name (str): The path to the template used to render the invitation form.
        permission_required (str): The permission required to access this view.
        form_class (InvitationForm): The form class used to handle user invitations.
    Methods:
        get_context_data(**kwargs):
            Adds the invitation form to the context data.
        post(request, *args, **kwargs):
            Handles the form submission, validates the form, creates an invitation, and sends an invitation email.
        send_invitation_email(invitation, request):
            Sends an email with the invitation link to the invited user.
    """
    template_name = 'user_app/company/create.html'
    permission_required = 'user_app.can_create_company'
    form_class = CompanyForm
    
    def get_context_data(self, **kwargs):
        return TemplateLayout.init(self, super().get_context_data(**kwargs))

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to render the invitation form.
        This method initializes the context with the invitation form and returns the rendered template.
        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        Returns:
            HttpResponse: Rendered template with the invitation form.
        """
        context = self.get_context_data()
        context['form'] = self.form_class()
        return self.render_to_response(context)
        
    def post(self, request, *args, **kwargs):
        
        " Create Form "
        instance_form = self.form_class(
            data=request.POST
        ) 
        
        if instance_form.is_valid():
            
            " Create Instance "
            instance = instance_form.save(request.user)
            
            return redirect(reverse("company_detail", args=[instance.id]))

            
        
        " Collect all errors if any form is invalid "
        context = self.get_context_data()
        context['form'] = instance_form
        
        return self.render_to_response(context)


###
#   Actions
#


@login_required
@require_GET
@permission_required('user_app.can_delete_company', raise_exception=True)
def company_delete(request, id):
    instance = get_object_or_404(Company, id=id)
    instance.delete()
    
    return redirect("companies")
