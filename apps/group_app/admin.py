from django.contrib import admin
from django import forms
from .models import Group, GroupInvite

class GroupInviteForm(forms.ModelForm):
    class Meta:
        model = GroupInvite
        fields = ['title', 'description', 'inviter', 'invited']

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'get_users', 'get_admins')
    search_fields = ('name', 'owner__username')
    list_filter = ('owner',)
    form = GroupInviteForm

    def get_users(self, obj):
        return ", ".join([user.username for user in obj.users.all()])
    get_users.short_description = 'Users'

    def get_admins(self, obj):
        return ", ".join([admin.username for admin in obj.admins.all()])
    get_admins.short_description = 'Admins'

class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ('title', 'inviter', 'invited', 'description')
    search_fields = ('title', 'inviter__name', 'invited__username')
    list_filter = ('inviter',)

admin.site.register(Group, GroupAdmin)
admin.site.register(GroupInvite, GroupInviteAdmin)