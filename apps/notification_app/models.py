from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Recipe,Comment
from ..common.models import BaseModel

# Create your models here.

class Notification(BaseModel):
    """
    Model to store notifications.
    """
    title = models.CharField(max_length=255)
    message = models.CharField(max_length=255)
    to_user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    from_user = models.ForeignKey(User,blank=True, null=True, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, blank=True, null=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment,blank=True, null=True, on_delete=models.CASCADE)
    seen = models.BooleanField(default=False)
    type = models.IntegerField(default=-1)