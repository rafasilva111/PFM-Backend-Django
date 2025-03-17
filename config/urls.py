###
#       General imports
##

##
#   Django 
#

from django.contrib import admin
from django.urls import include, path

##
#   Views 
#

from web_project.views import SystemView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Api
    path("api/v1/", include("apps.api.urls")),

    # Common
    path("", include("apps.common.urls")),
    
    # User App
    path("", include("apps.user_app.urls")),
    
    # Task App
    path("", include("apps.etl_app.urls")),
    
]

handler404 = SystemView.as_view(template_name="common/pages_misc_error.html", status=404)
handler400 = SystemView.as_view(template_name="common/pages_misc_error.html", status=400)
handler500 = SystemView.as_view(template_name="common/pages_misc_error.html", status=500)
