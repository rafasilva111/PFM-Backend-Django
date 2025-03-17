from django.urls import path, re_path

from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi


###
#   Views
##

from apps.user_app.api_views import LoginView,AuthView,UserView,UserListView,CustomTokenRefreshView

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

schema_view = get_schema_view(
openapi.Info(
    title="GoodBites API Documentation",
    default_version='v1',
    description="Test description",
    #terms_of_service="https://www.google.com/policies/terms/",
    #contact=openapi.Contact(email="contact@myapi.local"),
    #license=openapi.License(name="BSD License"),
),
public=True,
permission_classes=(permissions.AllowAny,),
)

urlpatterns = [


    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
  
    
    ###
    #
    #   User App
    #
    ##
    
    ###
    #   Auth
    ##
    
    path('auth', AuthView.as_view(), name="auth"), # Get, Register, Logout Session
    path('auth/login', LoginView.as_view(), name="login"), # Log in Session
    path('auth/refresh', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    ###
    #   User
    ##
    
    path('user', UserView.as_view(), name="user"), # get, post, put, delete user
    path('user/list', UserListView.as_view(), name="user_list"), # get users
    
    
    
    ###
    #
    #   Task App
    #
    ##
    
    # todo
    # check all tasks
    # check task
    # start task
    # stop
    # resume
    # pause
    
    

] 
