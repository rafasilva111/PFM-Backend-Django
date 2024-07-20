# admin.py

from django.contrib import admin
from .models import CalendarEntry

@admin.register(CalendarEntry)
class CalendarEntryAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'portion', 'realization_date', 'checked_done', 'tag')
    list_filter = ('realization_date', 'checked_done', 'tag', 'recipe', 'user')
    search_fields = ('recipe__name', 'user__username', 'tag')
    list_editable = ('checked_done', 'tag')
    date_hierarchy = 'realization_date'