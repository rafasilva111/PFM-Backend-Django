from django.contrib import admin
from .models import Notification

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'to_user', 'from_user', 'recipe', 'comment', 'seen', 'type')
    search_fields = ('title', 'message', 'to_user__username', 'from_user__username', 'recipe__name', 'comment__content')
    list_filter = ('seen', 'type', 'to_user', 'from_user')
    actions = ['mark_as_seen', 'mark_as_unseen', 'delete_selected']

    def mark_as_seen(self, request, queryset):
        queryset.update(seen=True)
        self.message_user(request, "Selected notifications marked as seen.")
    mark_as_seen.short_description = "Mark selected notifications as seen"

    def mark_as_unseen(self, request, queryset):
        queryset.update(seen=False)
        self.message_user(request, "Selected notifications marked as unseen.")
    mark_as_unseen.short_description = "Mark selected notifications as unseen"

admin.site.register(Notification, NotificationAdmin)