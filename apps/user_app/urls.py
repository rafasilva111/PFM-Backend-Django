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

from apps.user_app.views import UserTableView, InvitationView, UserDetailView, UserEditView, InvitationSuccessView, UserRegisterView, UserRegisterSuccessView,\
    user_enable, user_disable, user_delete,\
    CompanyTableView,CompanyDetailView, CompanyCreateView,CompanyEditView,\
    InvitationTableView,InvitationDetailView,InvitationEditView,\
    invite_delete, invite_resend
    

urlpatterns = [
    
    ###
    #
    #       User App
    #   
    ##


    path("users", UserTableView.as_view(), name="users"),
    path("user/<int:id>", UserDetailView.as_view(), name="user_detail"),
    path("user/<int:id>/edit", UserEditView.as_view(), name="user_edit"),
    path("user/<int:id>/enable", user_enable, name="user_enable"),
    path("user/<int:id>/disable", user_disable, name="user_disable"),
    path("user/<int:id>/delete", user_delete, name="user_delete"),
    

    ##
    #   Invitations
    #
    
    path("user/invite", InvitationView.as_view(), name="user_invite"),
    path("user/invite/success", InvitationSuccessView.as_view(), name="invite_success"),
    path("user/register/<uuid:token>", UserRegisterView.as_view(), name="user_register"),
    path("user/register/success", UserRegisterSuccessView.as_view(), name="user_register_success"),
    
    path("user/invites", InvitationTableView.as_view(), name="invites"),
    path("user/invite/<int:id>", InvitationDetailView.as_view(), name="invite_detail"),
    path("user/invite/<int:id>/edit", InvitationEditView.as_view(), name="invite_edit"),
    path("user/invite/<int:id>/resend", invite_resend, name="invite_resend"),
    path("user/invite/<int:id>/delete", invite_delete, name="invite_delete"),
    
    ##
    #   Company
    #
    
    path("companies", CompanyTableView.as_view(), name="companies"),
    path("company/create", CompanyCreateView.as_view(), name="company_create"),
    path("company/<int:id>", CompanyDetailView.as_view(), name="company_detail"),
    path("company/<int:id>/edit", CompanyEditView.as_view(), name="company_edit"),
    path("company/<int:id>/delete", user_delete, name="company_delete"),
    
] 
