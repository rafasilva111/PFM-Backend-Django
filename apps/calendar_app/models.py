from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Recipe
from apps.common.models import BaseModel

class CalendarEntry(BaseModel):
    """
    Model to store calendar entries.
    """

    
    recipe = models.ForeignKey(Recipe, related_name='calendar_entries', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='calendar_entries', on_delete=models.CASCADE)
    portion = models.IntegerField(null=True)
    realization_date = models.DateTimeField()
    checked_done = models.BooleanField(default=False)
    
    class Tag(models.TextChoices):
        PEQUENO_ALMOCO = 'Breakfast', 'Pequeno Almoço'
        LANCHE_DA_MANHA = 'Morning Snack', 'Lanche da manhã'
        ALMOCO = 'Lunch', 'Almoço'
        LANCHE_DA_TARDE = 'Afternoon Snack', 'Lanche da tarde'
        JANTAR = 'Dinner', 'Jantar'
        CEIA = 'Supper', 'Ceia'
        OTHER = 'Other', 'Other'

    tag = models.CharField(
        max_length=15,
        choices=Tag.choices,
        default=Tag.OTHER,
    )