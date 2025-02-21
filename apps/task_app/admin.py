###
# General imports
##

## Django Admin
from django.contrib import admin

### App-specific imports

## Models
from apps.task_app.models import Task, Job, TimeCondition  # Add this import

# Register your models here.

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Task model.

    - Displays task type, status, and timing information.
    - Provides an action to duplicate selected tasks.

    Attributes:
        list_display (tuple): Fields to display in the list view.
        actions (list): List of custom actions for TaskAdmin.
    """
    list_display = ('type', 'status', 'started_at', 'finished_at')
    actions = ['duplicate_tasks']

    def duplicate_tasks(self, request, queryset):
        """
        Duplicates selected Task instances.

        - For each task in the queryset, sets the primary key to None,
          saving it as a new instance.
          
        Args:
            request (HttpRequest): The current request object.
            queryset (QuerySet): The selected tasks to duplicate.
        """
        for task in queryset:
            task.pk = None  # Set primary key to None to create a new instance
            task.save()
    duplicate_tasks.short_description = 'Duplicate selected tasks'


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Job model.

    - Displays the last run time and allows filtering by it.
    - Sets last_run as a read-only field.

    Attributes:
        list_display (tuple): Fields to display in the list view.
        list_filter (tuple): Fields to filter by in the list view.
        readonly_fields (tuple): Fields to set as read-only.
    """
    list_display = ('name', 'type', 'enabled', 'continue_mode', 'starting_condition', 'stopping_condition', 'log_path')
    search_fields = ('name', 'type','enabled')
    list_filter = ('continue_mode', 'type')
    readonly_fields = ('starting_condition', 'stopping_condition')
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'continue_mode', 'log_path')
        }),
        ('Conditions', {
            'fields': ('starting_condition', 'stopping_condition')
        }),
    )



@admin.register(TimeCondition)
class TimeConditionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the TimeCondition model.

    - Displays crontab and periodic task information.
    - Allows searching by crontab schedule.

    Attributes:
        list_display (tuple): Fields to display in the list view.
        search_fields (tuple): Fields to search by in the list view.
    """
    list_display = ('id', 'periodic_task')


