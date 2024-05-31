from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Recipe


class CalendarEntry(models.Model):
    """
    Model to store calendar entries.
    """
    PEQUENO_ALMOCO = 'PEQUENO ALMOÇO'
    LANCHE_DA_MANHA = 'LANCHE DA MANHÃ'
    ALMOCO = 'ALMOÇO'
    LANCHE_DA_TARDE = 'LANCHE DA TARDE'
    JANTAR = 'JANTAR'
    CEIA = 'CEIA'

    TAG_CHOICES = [
        (PEQUENO_ALMOCO, 'Pequeno almoço'),
        (LANCHE_DA_MANHA, 'Lanche da manhã'),
        (ALMOCO, 'Almoço'),
        (LANCHE_DA_TARDE, 'Lanche da tarde'),
        (JANTAR, 'Jantar'),
        (CEIA, 'Ceia'),
    ]

    recipe = models.ForeignKey(Recipe, related_name='calendar_entries', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='calendar_entries', on_delete=models.CASCADE)
    tag = models.CharField(max_length=255, choices=TAG_CHOICES)
    portion = models.IntegerField(null=True)
    realization_date = models.DateTimeField()
    checked_done = models.BooleanField(default=False)