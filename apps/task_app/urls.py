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

from apps.task_app.views import JobTableView, JobCreateView , JobDetailView, JobEditView, job_delete, job_pause, job_resume\
    , TaskTableView, TaskDetailView, TaskCreateView, TaskEditView, task_delete, task_restart, task_cancel, task_pause, task_resume


###
#
#       Task App
#   
##

urlpatterns = [

    ###
    #   Jobs
    ##

    path("jobs", JobTableView.as_view(), name="jobs"),
    path("job/create", JobCreateView.as_view(), name="job_create"),
    path("job/<int:id>", JobDetailView.as_view(), name="job_detail"),
    path("job/<int:id>/edit", JobEditView.as_view(), name="job_edit"),
    path("job/<int:id>/resume", job_resume, name="job_resume"),
    path("job/<int:id>/pause", job_pause, name="job_pause"),
    path("job/<int:id>/delete", job_delete, name="job_delete"),
    
    
    ###
    #   Tasks
    ##

    path("tasks", TaskTableView.as_view(), name="tasks"),
    path("task/create", TaskCreateView.as_view(), name="task_create"),
    path("task/<int:id>", TaskDetailView.as_view(), name="task_detail"),
    path("task/<int:id>/edit", TaskEditView.as_view(), name="task_edit"),
    path("task/<int:id>/restart", task_restart, name="task_restart"),
    path("task/<int:id>/cancel", task_cancel, name="task_cancel"),
    path("task/<int:id>/pause", task_pause, name="task_pause"),
    path("task/<int:id>/resume", task_resume, name="task_resume"),
    path("task/<int:id>/delete", task_delete, name="task_delete"),

]
