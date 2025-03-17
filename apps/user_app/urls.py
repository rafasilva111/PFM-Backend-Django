###
#       General imports
##

##
#   Django 
#

from django.urls import  path

##
#   Views 
#

from apps.user_app.views import UserTableView, UserInviteView, UserDetailView, UserEditView, UserInviteSuccessView, UserRegisterView, UserRegisterSuccessView,\
    user_enable_disable, user_delete

urlpatterns = [
    
    ###
    #
    #       User App
    #   
    ##


    path("users", UserTableView.as_view(), name="users"),
    path("user/invite", UserInviteView.as_view(), name="user_invite"),
    path("user/invite/success", UserInviteSuccessView.as_view(), name="user_invite_success"),
    path("user/register/<uuid:token>", UserRegisterView.as_view(), name="user_register"),
    path("user/register/success", UserRegisterSuccessView.as_view(), name="user_register_success"),
    path("user/<int:id>", UserDetailView.as_view(), name="user_detail"),
    path("user/<int:id>/edit", UserEditView.as_view(), name="user_edit"),
    path("user/<int:id>/disable", user_enable_disable, name="user_enable_disable"),
    path("user/<int:id>/delete", user_delete, name="user_delete"),
    

] 
