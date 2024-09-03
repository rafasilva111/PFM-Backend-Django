from django.contrib import admin
from .models import User, Company, FollowRequest, Follow


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'name', 'birth_date', 'is_active', 'created_at', 'user_type')
    list_filter = ('is_active', 'user_type')
    search_fields = ('email', 'username', 'name')
    ordering = ('-created_at',)

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'imgs_bucket')
    search_fields = ('name',)
    

class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed')
    search_fields = ('follower__email', 'follower__username', 'followed__email', 'followed__username')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed')
    search_fields = ('follower__email', 'follower__username', 'followed__email', 'followed__username')
    

admin.site.register(User, UserAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(FollowRequest, FollowRequestAdmin)
admin.site.register(Follow, FollowAdmin)
