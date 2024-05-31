from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.views import View
from .forms import LoginForm,RegisterForm,ResetForm
from .models import User

import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyDrma6XqL6Qyw3E5WnGS7iKnht2Ea8gksU",
    "authDomain": "projetofoodmanager.firebaseapp.com",
    "databaseURL": "https://projetofoodmanager-default-rtdb.europe-west1.firebasedatabase.app",
    "projectId": "projetofoodmanager",
    "storageBucket": "projetofoodmanager.appspot.com",
    "messagingSenderId": "1060802135704",
    "appId": "1:1060802135704:web:c3c91e650e38fa7fe532ed",
    "measurementId": "G-216ZE9KDML"
  }

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# =========================
# Authentication 
# =========================
# Description: Authentication views.
# Author: Rafael Silva
# Date: May 12, 2024

class LoginView(View):
    def get(self, request):
        form = LoginForm()
        return render(request, "accounts/login.html", {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                # Firebase Auth
                user = auth.sign_in_with_email_and_password(email, password)
                #
                django_user = User.objects.get(email=email)
                # Django Auth
                login(request, django_user)
                
                return redirect("/")
            except:
                # Handle authentication errors
                form.add_error(None, "Invalid email or password")
        return render(request, 'accounts/login.html', {'form': form})
    
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
                firebase_auth = auth.create_user_with_email_and_password(email, password)
                return redirect('login', {"msg":"User register succesfully, please login"})
            
            except Exception as e:
                error_message = e.args[1] if len(e.args) > 1 else e.args[0]
                if "EMAIL_EXISTS" in error_message:
                    form.add_error("email", f"Email already exist.")
                else:
                    form.add_error("password2", f"{error_message}")

                
        return render(request, 'accounts/register.html', {'form': form})
    
class ResetView(View):
    def get(self, request):
        form = ResetForm()
        return render(request, "accounts/reset.html", {'form': form})

    
    def post(self, request):
        form = ResetForm(request.POST)
        if form.is_valid():
            email = request.POST.get('email')
            try:
                auth.send_password_reset_email(email)
                message  = "A email to reset password is successfully sent"
                return render(request, "accounts/reset.html", {"msg":message})
            except:
                message  = "Something went wrong, Please check the email you provided is registered or not"
                return render(request, "Reset.html", {"msg":message})
        return render(request, "accounts/reset.html", {'form': form})

    

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('signIn')
    



