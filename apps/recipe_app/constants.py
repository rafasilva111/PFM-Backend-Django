
from enum import Enum
from django.db import models

class RecipeSortingTypes(models.TextChoices):
    VERIFIED = "VERIFIED","Verified"
    DATE = "DATE", "Date"
    LIKES = "LIKES", "Likes"
    SAVES = "SAVES", "Saves"
    RANDOM = "RANDOM","Random"
    CLASSIFICATION = "CLASSIFICATION", "Classification"

    @classmethod
    def is_valid_choice(cls, value):

        return value in cls.values



class RecipesBackgroundType(models.TextChoices):
    LIKED = "L", "Liked"
    SAVED = "S","Saved"
