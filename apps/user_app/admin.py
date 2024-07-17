from django.contrib import admin
from .models import User, Company, Goal, FollowRequest, Follow


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'name', 'birth_date', 'is_active', 'created_at', 'user_type')
    list_filter = ('is_active', 'user_type')
    search_fields = ('email', 'username', 'name')
    ordering = ('-created_at',)

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'imgs_bucket')
    search_fields = ('name',)
    

class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal', 'calories', 'fat_upper_limit', 'fat_lower_limit', 'saturated_fat',
                    'carbohydrates', 'proteins_upper_limit', 'proteins_lower_limit')
    list_filter = ('user',)
    search_fields = ('user__email', 'user__username')


class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed')
    search_fields = ('follower__email', 'follower__username', 'followed__email', 'followed__username')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed')
    search_fields = ('follower__email', 'follower__username', 'followed__email', 'followed__username')
    

admin.site.register(User, UserAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Goal, GoalAdmin)
admin.site.register(FollowRequest, FollowRequestAdmin)
admin.site.register(Follow, FollowAdmin)
