from django.contrib import admin
from apps.user_app.models import User, Invitation, Company
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin



class UserAdmin(BaseUserAdmin):
    list_display = ('email','is_active', 'created_at', 'type')
    list_filter = ('is_active', 'type')
    search_fields = ('email',)
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('type',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )

    
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'token', 'invited_by', 'created_at')
    list_filter = ( 'created_at', 'invited_by')
    search_fields = ('email', 'token', 'invited_by__email')
    readonly_fields = ('token', 'created_at')


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_account',)
    search_fields = ('name',)
    ordering = ('name',)

admin.site.register(User, UserAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Company, CompanyAdmin)
