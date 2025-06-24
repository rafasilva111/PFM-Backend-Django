###
#       General imports
##

##
#   Django 
#

from django.contrib import admin
from django.urls import  path, include
from django.views.static import serve
from django.conf import settings

##
#   Third Party
#

import os

##
#   Views 
#

from apps.common.views import DashboardsView, ReadMeView,TermsAndConditionsView, total_task_chart_data,total_task_report_chart_data
from apps.user_app.views import LoginView,RegisterView,LogoutView,\
    PasswordResetView,PasswordResetDoneView,PasswordResetConfirmView,PasswordResetCompleteView
from django.views.generic import TemplateView
##
#   Views 
#

from web_project.views import SystemView

urlpatterns = [
    
    
    
    
    ###
    #
    #       Common App
    #   
    ##

    path("", DashboardsView.as_view(), name="home"),
    
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
    path("terms_and_conditions", TermsAndConditionsView.as_view(), name="terms_and_conditions"),
    
    path("total-task-chart-data", total_task_chart_data, name="total_task_chart_data"),
    path("total-task-report-chart-data", total_task_report_chart_data, name="total_task_report_chart_data"),
    
    path('docs/', TemplateView.as_view(template_name='index.html')),
    path('docs/<path:path>', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'docs/build/html'),
    }),
    
    
    ###
    #   Admin Routes
    ##
    
    path("admin/", admin.site.urls),


    ###
    #
    #       API App
    #   
    ##
    
    path("api/v1/", include("apps.api.urls")),

    
    ###
    #
    #       User App
    #   
    ##
    
    path("", include("apps.user_app.urls")),
    
    
    ###
    #
    #       ETL App
    #   
    ##
    
    path("", include("apps.etl_app.urls")),
    
    ###
    #
    #       Recipe App
    #   
    ##
    
    path("", include("apps.recipe_app.urls")),
    
    
]

handler404 = SystemView.as_view(template_name="common/pages_misc_error.html", status=404)
handler400 = SystemView.as_view(template_name="common/pages_misc_error.html", status=400)
handler500 = SystemView.as_view(template_name="common/pages_misc_error.html", status=500)
