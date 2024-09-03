from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.views import View
from .forms import LoginForm, RegisterForm, ResetForm
from .models import User
from django.views.generic import TemplateView
from web_project import TemplateLayout, TemplateHelper
from django.conf import settings

# =========================
# Authentication 
# =========================
# Description: Authentication views.
# Author: Rafael Silva
# Date: May 12, 2024

"""class LoginView(View):
    def get(self, request):
        form = LoginForm()
        return render(request, "accounts/login.html", {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                # Django Auth
                login(request, user)
                return redirect("/")
            else:
                # Handle authentication errors
                form.add_error(None, "Invalid email or password")
        return render(request, 'accounts/login.html', {'form': form})"""
    
    
class LoginView(TemplateView):
    template_name = 'user_app/auth/login.html'  # Assuming the login template path
    form = LoginForm()

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path']  = TemplateHelper.set_layout("layout_blank.html", context)
        context['form'] = self.form

        return context

    def post(self, request):
        self.form = LoginForm(request.POST)
        if self.form.is_valid():
            email = self.form.cleaned_data['email']
            password = self.form.cleaned_data['password']
            remember_me  = self.form.cleaned_data['remember_me']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)


                if remember_me:
                    # If remember_me is checked, set a longer session expiry time
                    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                else:
                    # If remember_me is not checked, use the default session expiry time
                    request.session.set_expiry(0)  # Expire at browser close

                return redirect("home")
            else:
                self.form.add_error(None, "Invalid email or password")
        # If form is invalid or authentication failed, pass form with errors back to template
        context = self.get_context_data(form=self.form)  
        return render(request, self.template_name, context)
     
class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
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
    
class ResetView(View):
    def get(self, request):
        form = ResetForm()
        return render(request, "accounts/reset.html", {'form': form})
    
    def post(self, request):
        form = ResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                # Assume you have a method to send reset email
                #send_reset_email(email)
                message = "An email to reset your password has been successfully sent"
                return render(request, "accounts/reset.html", {"msg": message})
            except Exception as e:
                message = "Something went wrong. Please check if the email you provided is registered."
                form.add_error(None, message)
        return render(request, "accounts/reset.html", {'form': form})

class LogoutView(View):

    def post(self, request):
        logout(request)
        # You can add additional logic for handling POST requests if needed
        return redirect('login')