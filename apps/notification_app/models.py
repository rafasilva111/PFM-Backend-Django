from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Recipe,Comment

# Create your models here.

# Notification App models
class Notification(models.Model):
    """
    Model to store notifications.
    """
    title = models.CharField(max_length=255)
    message = models.CharField(max_length=255)
    to_user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    from_user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, null=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, on_delete=models.CASCADE)
    seen = models.BooleanField(default=False)
    type = models.IntegerField(default=-1)