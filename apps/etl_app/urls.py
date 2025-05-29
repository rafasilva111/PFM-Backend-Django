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

from apps.etl_app.views import JobTableView, JobCreateView , JobDetailView, JobEditView, job_delete, job_enable, job_disable, job_force_start\
    , TaskTableView, TaskDetailView, TaskCreateView, TaskEditView, task_delete, task_restart, task_cancel, task_pause, task_resume, download_log, download_db


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
    path("job/<int:id>/force_start", job_force_start, name="job_force_start"),
    path("job/<int:id>/enable", job_enable, name="job_enable"),
    path("job/<int:id>/disable", job_disable, name="job_disable"),
    path("job/<int:id>/delete", job_delete, name="job_delete"),
    path("job/<int:id>/log/clear", download_log, name="job_log_clear"),
    path("job/<int:id>/log/download", download_log, name="job_log_download"),
    
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
    path("task/<int:id>/log/clear", download_log, name="task_log_clear"),
    path("task/<int:id>/log/download", download_log, name="task_log_download"),
    path("task/<int:id>/db/download", download_db, name="task_db_download"),

    ##
    #   Miscellaneous
    ##
    
    path("terms", TaskTableView.as_view(), name="terms"),
]
