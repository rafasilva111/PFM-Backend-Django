from django.db import models
from django.db.models import Avg, Count
from apps.user_app.models import User
from apps.common.models import BaseModel



class Ingredient(models.Model):
    """
    Model to store information about ingredients.
    """
    name = models.CharField(max_length=255)

class RecipeIngredientQuantity(models.Model):
    """
    Model to store quantities of ingredients for recipes.
    """
    ingredient = models.ForeignKey(Ingredient, related_name='ingredient_base', on_delete=models.CASCADE)
    recipe = models.ForeignKey("Recipe", related_name='ingredients', on_delete=models.CASCADE)
    quantity_original = models.CharField(max_length=255)
    quantity_normalized = models.FloatField(null=True)
    units_normalized = models.CharField(default='G', max_length=255)
    extra_quantity = models.FloatField(null=True)
    extra_units = models.CharField(max_length=255, null=True)

class NutritionInformation(models.Model):
    """
    Model to store nutrition information for recipes.
    """
    energia = models.FloatField(null=True)
    energia_perc = models.FloatField(null=True)
    gordura = models.FloatField(null=True)
    gordura_perc = models.FloatField(null=True)
    gordura_saturada = models.FloatField(null=True)
    gordura_saturada_perc = models.FloatField(null=True)
    hidratos_carbonos = models.FloatField(null=True)
    hidratos_carbonos_perc = models.FloatField(null=True)
    hidratos_carbonos_acucares = models.FloatField(null=True)
    hidratos_carbonos_acucares_perc = models.FloatField(null=True)
    fibra = models.FloatField(null=True)
    fibra_perc = models.FloatField(null=True)
    proteina = models.FloatField(null=True)
    proteina_perc = models.FloatField(null=True)


class Recipe(BaseModel):
    title = models.CharField(max_length=255, null=False)
    description = models.TextField( null=False)
    img_source = models.CharField(max_length=255, null=True)
    verified = models.BooleanField(default=False)
    difficulty = models.CharField(max_length=255, null=True)
    portion = models.CharField(max_length=255, null=True)
    time = models.CharField(max_length=255, null=True)
    views = models.IntegerField(default=0, null=False)
    created_by = models.ForeignKey(User, related_name='created_recipes', on_delete=models.CASCADE)
    nutrition_information = models.ForeignKey(NutritionInformation, related_name='recipe', null=True, on_delete=models.CASCADE)
    rating = models.FloatField(default=0)
    source_rating = models.FloatField(null=True)
    source_link = models.CharField(max_length=255, null=True,unique=True)
    
    users_liked = models.ManyToManyField(User, related_name='liked_recipes')
    users_saved = models.ManyToManyField(User, related_name='saved_recipes')

    def get_average_rating(self):
        return self.ratings.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0


    class Meta:
        ordering = ['-views']  # Order recipes by views in descending order


class Preparation(BaseModel):
    """
    Model to store tags for recipes.
    """
    step = models.CharField(max_length=2)
    description = models.TextField()
    recipe = models.ForeignKey(Recipe,on_delete=models.CASCADE, related_name='preparation')

class Tag(BaseModel):
    """
    Model to store tags for recipes.
    """
    title = models.CharField(max_length=255)
    recipes = models.ManyToManyField(Recipe, related_name='tags')


class RecipeRating(BaseModel):
    """
    Model to store ratings for recipes.
    """
    recipe = models.ForeignKey(Recipe, related_name='ratings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='rated_recipes', on_delete=models.CASCADE)
    rating = models.IntegerField(null=True)

class RecipeBackground(BaseModel):
    """
    Model to store background information for recipes.
    """
    user = models.ForeignKey(User, related_name='recipes', on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, related_name='backgrounds', on_delete=models.CASCADE)
    type = models.CharField(max_length=255)



class Comment(BaseModel):
    """
    Model to store comments on recipes.
    """
    text = models.CharField(max_length=255)
    recipe = models.ForeignKey(Recipe, related_name='comments', on_delete=models.CASCADE, null=True)
    parent_comment = models.ForeignKey('self', related_name='comments', on_delete=models.CASCADE, null=True)
    likes = models.ManyToManyField(User, related_name='comment_likes')
    user = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)

class RecipeReport(BaseModel):
    """
    Model to store reports on recipes.
    """
    title = models.CharField(max_length=255)
    message = models.CharField(max_length=255)
    recipe = models.ForeignKey(Recipe, related_name='reports', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='recipe_reports', on_delete=models.CASCADE)
    
    class Satus(models.TextChoices):
        RESOLVED = 'RESOLVED', 'Resolved'
        SEEN = 'SEEN', 'Seen'
        PENDING = 'PENDING', 'Pending'

    status = models.CharField(
        max_length=10,
        choices=Satus.choices,
        default=Satus.PENDING,
        null=True
    )
    
