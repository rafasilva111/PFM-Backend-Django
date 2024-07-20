from django.urls import path
from .views import DashboardsView,ReadMeView
from apps.recipe_app.views import RecipeTaskTableView,RecipeTaskCreateView,RecipeTaskDetailView,recipe_task_restart,recipe_task_pause,recipe_task_resume,\
    recipe_task_delete,recipe_task_cancel,\
    RecipeTableView,RecipeDetailView,recipe_delete,\
    RecipeReportTableView,RecipeReportCreateView,RecipeReportDetailView
from apps.etl_app.views import JobTableView, JobCreateView ,JobDetailView, job_delete,job_pause,job_resume
from apps.authentication.views import AuthView
from apps.user_app.views import LoginView,RegisterView,ResetView,LogoutView

urlpatterns = [
    path("", DashboardsView.as_view(), name="home"),


    ###
    #
    #       User App
    #   
    ##


    path('login', LoginView.as_view(), name="login"),
    path('register', RegisterView.as_view(), name="register"),
    path('reset', ResetView.as_view(), name="reset"),
    path('logout', LogoutView.as_view(), name="logout"), 


    ###
    #
    #       Recipe App
    #   
    ##

    ###
    #   Jobs
    ##

    path("jobs", JobTableView.as_view(), name="job"),
    path("job/create", JobCreateView.as_view(), name="job_create"),
    path("job/<int:id>", JobDetailView.as_view(), name="job_detail"),
    path("job/<int:id>/resume", job_resume, name="job_resume"),
    path("job/<int:id>/pause", job_pause, name="job_pause"),
    path("job/<int:id>/delete", job_delete, name="job_delete"),

    ###
    #   Ingredients
    ##

    # General

    path("ingredients", RecipeTableView.as_view(), name="ingredient"),

    # ETL Tasks

    path("ingredient/tasks", RecipeTaskTableView.as_view(), name="ingredient_tasks"),
    path("ingredient/task/create", RecipeTaskCreateView.as_view(), name="ingredient_task_create"),
    path("ingredient/task/<int:id>", RecipeTaskDetailView.as_view(), name="ingredient_task_detail"),
    path("ingredient/task/<int:id>/restart", recipe_task_restart, name="ingredient_task_restart"),
    path("ingredient/task/<int:id>/pause", recipe_task_pause, name="ingredient_task_pause"), #todo
    path("ingredient/task/<int:id>/resume", recipe_task_resume, name="ingredient_task_resume"),#todo
    path("ingredient/task/<int:id>/cancel", recipe_task_cancel, name="ingredient_task_cancel"),
    path("ingredient/task/<int:id>/delete", recipe_task_delete, name="ingredient_task_delete"),

    # Reports  

    path("ingredient/reports", RecipeTaskTableView.as_view(), name="ingredient_reports"),


    ###
    #   Recipes
    ##

    # General

    path("recipes", RecipeTableView.as_view(), name="recipe"),
    path("recipe/<int:id>", RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/<int:id>/edit", RecipeTableView.as_view(), name="recipe"),
    path("recipe/<int:id>/delete", recipe_delete, name="recipe_delete"),

    path("recipe/<int:id>/report/create", RecipeReportCreateView.as_view(), name="recipe_report_create"),

    # ETL Tasks

    path("recipe/tasks", RecipeTaskTableView.as_view(), name="recipe_tasks"),
    path("recipe/task/create", RecipeTaskCreateView.as_view(), name="recipe_task_create"),
    path("recipe/task/<int:id>", RecipeTaskDetailView.as_view(), name="recipe_task_detail"),
    path("recipe/task/<int:id>/restart", recipe_task_restart, name="recipe_task_restart"),
    path("recipe/task/<int:id>/pause", recipe_task_pause, name="recipe_task_pause"), #todo
    path("recipe/task/<int:id>/resume", recipe_task_resume, name="recipe_task_resume"),#todo
    path("recipe/task/<int:id>/cancel", recipe_task_cancel, name="recipe_task_cancel"),
    path("recipe/task/<int:id>/delete", recipe_task_delete, name="recipe_task_delete"),

    # Reports

    path("recipe/reports", RecipeReportTableView.as_view(), name="recipe_reports"),
    path("recipe/report/<int:id>", RecipeReportDetailView.as_view(), name="recipe_report_detail"),
    

    ###
    #   Misc
    ##

    path("readme", ReadMeView.as_view(), name="readme"),
]

