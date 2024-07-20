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
        PEQUENO_ALMOCO = 'PEQUENO ALMOÇO', 'Pequeno almoço'
        LANCHE_DA_MANHA = 'LANCHE DA MANHÃ', 'Lanche da manhã'
        ALMOCO = 'ALMOÇO', 'Almoço'
        LANCHE_DA_TARDE = 'LANCHE DA TARDE', 'Lanche da tarde'
        JANTAR = 'JANTAR', 'Jantar'
        CEIA = 'CEIA', 'Ceia'
        OTHER = 'OTHER', 'Other'

    tag = models.CharField(
        max_length=15,
        choices=Tag.choices,
        default=Tag.OTHER,
    )