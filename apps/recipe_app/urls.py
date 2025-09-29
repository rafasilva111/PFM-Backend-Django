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

from apps.recipe_app.views import RecipeTableView,  RecipeDetailView,  recipe_delete, \
    AuditLogTableView, AuditLogDetailView, audit_log_delete, audit_log_accept,audit_log_unaccept, audit_log_review, audit_log_unreview,\
    RecipeReportTableView, RecipeReportDetailView, RecipeReportCreateView, recipe_report_delete, recipe_report_review, recipe_report_unreview

###
#
#       Task App
#   
##

urlpatterns = [

    ###
    #   Recipe
    ##

    path("recipes", RecipeTableView.as_view(), name="recipes"),
    path("recipe/<int:id>", RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/<int:id>/delete", recipe_delete, name="recipe_delete"),
    
    
    ###
    #   Audit Log
    ##

    path("recipe/audit_logs", AuditLogTableView.as_view(), name="audit_logs"),
    path("recipe/audit_log/<int:id>", AuditLogDetailView.as_view(), name="audit_log_detail"),
    path("recipe/audit_log/<int:id>/delete", audit_log_delete, name="audit_log_delete"),
    path("recipe/audit_log/<int:id>/accept", audit_log_accept, name="audit_log_accept"),
    path("recipe/audit_log/<int:id>/unaccept", audit_log_unaccept, name="audit_log_unaccept"),
    path("recipe/audit_log/<int:id>/review", audit_log_review, name="audit_log_review"),
    path("recipe/audit_log/<int:id>/unreview", audit_log_unreview, name="audit_log_unreview"),
    
    ###
    #   Recipe Reports
    ##
    
    path("recipe/reports", RecipeReportTableView.as_view(), name="recipe_reports"),
    path("recipe/report/create", RecipeReportCreateView.as_view(), name="recipe_report_create"),
    path("recipe/report/<int:id>", RecipeReportDetailView.as_view(), name="recipe_report_detail"),
    path("recipe/report/<int:id>/delete", recipe_report_delete, name="recipe_report_delete"),
    path("recipe/report/<int:id>/review", recipe_report_review, name="recipe_report_review"),
    path("recipe/report/<int:id>/unreview", recipe_report_unreview, name="recipe_report_unreview")
]
