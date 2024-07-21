from django.contrib import admin
from apps.etl_app.models import Task,Job   

# Register your models here.

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('get_company_name', 'type', 'status', 'started_at', 'finished_at')
    actions = ['duplicate_tasks']

    def get_company_name(self, obj):
        return obj.company.name
    get_company_name.short_description = 'Company'
    
    def duplicate_tasks(self, request, queryset):
        for task in queryset:
            task.pk = None  # This sets the primary key to None, creating a new instance
            task.save()
    duplicate_tasks.short_description = 'Duplicate selected tasks'
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('get_company_name', 'crontab', 'periodic_task', 'last_run')
    search_fields = ('get_company_name',)
    list_filter = ('last_run',)
    readonly_fields = ('periodic_task', 'last_run')

    def get_company_name(self, obj):
        return obj.user.name
    get_company_name.short_description = 'Company'

    def save_model(self, request, obj, form, change):
        # Custom save logic to handle the creation of PeriodicTask if not exists
        obj.save()

