###
#       Default imports
##


##
#   Default
#

from django.db import models



###
#       App specific imports
##


##
#   Models
#

from apps.common.models import BaseModel



###
#
#   Goal App
#
##

###
#   Diet
##

    
class Diet(BaseModel):
    name = models.CharField(max_length=40, null=False)
    min_carbohydrates = models.IntegerField( null=False)
    max_carbohydrates = models.IntegerField(null=False)
    min_fats = models.IntegerField(null=False)
    max_fats = models.IntegerField(null=False)
    min_proteins = models.IntegerField(null=False)
    max_proteins = models.IntegerField(null=False)
    description = models.CharField(max_length=150, null=False)
    
    def __str__(self):
        return self.name
    

###
#   Goal
##
 
class Goal(BaseModel):

    name = models.CharField(max_length=40, null=False)
    username = models.CharField(max_length=255, null=False, unique=True)
    description = models.CharField(max_length=255, default='',blank=True)
    diet = models.ForeignKey(Diet,related_name="goals", on_delete=models.CASCADE)
    user = models.OneToOneField(Diet, on_delete=models.CASCADE)