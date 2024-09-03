###
#       Default imports
##


##
#   Default
#

from django.contrib import admin



###
#       App specific imports
##


##
#   Models
#

from apps.goal_app.models import Goal,Diet



###
#
#   Goal App
#
##

###
#   Goal
##

class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal', 'calories', 'fat_upper_limit', 'fat_lower_limit', 'saturated_fat',
                    'carbohydrates', 'proteins_upper_limit', 'proteins_lower_limit')
    list_filter = ('user',)
    search_fields = ('user__email', 'user__username')



###
#   Diet
##

class DietAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal', 'calories', 'fat_upper_limit', 'fat_lower_limit', 'saturated_fat',
                    'carbohydrates', 'proteins_upper_limit', 'proteins_lower_limit')
    list_filter = ('user',)
    search_fields = ('user__email', 'user__username')
    

admin.site.register(Diet, DietAdmin)
admin.site.register(Goal, GoalAdmin)
