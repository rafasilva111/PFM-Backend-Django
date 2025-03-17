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

from apps.common.views import DashboardsView,ReadMeView, total_task_chart_data,total_task_report_chart_data
from apps.user_app.views import LoginView,RegisterView,LogoutView,PasswordResetView,PasswordResetDoneView,PasswordResetConfirmView,PasswordResetCompleteView



urlpatterns = [
    
    path("", DashboardsView.as_view(), name="home"),
    
    path("total-task-chart-data", total_task_chart_data, name="total_task_chart_data"),
    path("total-task-report-chart-data", total_task_report_chart_data, name="total_task_report_chart_data"),


    ###
    #
    #       Common App
    #   
    ##


    path('login', LoginView.as_view(), name="login"),
    path('register', RegisterView.as_view(), name="register"),
    path('logout', LogoutView.as_view(), name="logout"), 
    
    path('password_reset', PasswordResetView.as_view(), name="password_reset"),
    path('password_reset/done', PasswordResetDoneView.as_view(), name="password_reset_done"),
    path('reset/<uidb64>/<token>', PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path('reset/done', PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    

    ###
    #   Misc
    ##

    path("readme", ReadMeView.as_view(), name="readme"),
]

