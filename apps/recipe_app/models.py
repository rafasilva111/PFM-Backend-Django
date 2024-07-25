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
    nutrition_information = models.OneToOneField(NutritionInformation, related_name='recipe', null=True, on_delete=models.CASCADE)
    rating = models.FloatField(default=0)
    source_rating = models.FloatField(null=True)
    source_link = models.CharField(max_length=255, null=True,unique=True)
    
    users_liked = models.ManyToManyField(User, related_name='liked_recipes', blank=True)
    users_saved = models.ManyToManyField(User, related_name='saved_recipes', blank=True)

    def get_average_rating(self):
        return self.ratings.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0

    def save_audited(self, *args, **kwargs):
            
            # Recipe Audit Log changing user
            
            if self.pk is not None:
                user = kwargs.pop('user', None)  # Remove 'user' from kwargs if present, or default to None
        
                if user is None:
                    # Assuming you have access to request object in the view or other context
                    if hasattr(self, '_request') and self._request.user.is_authenticated:
                        user = self._request.user
                    else:
                        raise ValueError("User must be provided or authenticated to save this model.")
                
                # Retrieve the current instance from the database
                old_instance = self.__class__.objects.get(pk=self.pk)
                

                
                for field in self._meta.fields:
                    if getattr(self, field.attname) != getattr(old_instance, field.attname):
                        RecipeAuditLog.objects.create(
                            recipe=self, field=field,
                            old_value=getattr(old_instance, field.attname),
                            new_value=getattr(self, field.attname),
                            user=kwargs['user']
                            ) 

                


            super(Recipe, self).save(*args, **kwargs)

            

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


# to be removed
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
    user = models.ForeignKey(User, related_name='my_recipe_reports', on_delete=models.CASCADE)
    assigne = models.ForeignKey(User, related_name='recipe_reports', on_delete=models.CASCADE)
    

    class Type(models.TextChoices):
        NutritionInformation = 'NutritionInformation', 'Nutrition Information'
        Ingredient = 'Ingredient', 'Ingredient'
        Preparation = 'Preparation', 'Preparation'
        Detail = 'Detail', 'Detail'
        Other = 'Other', 'Other'

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.Other,
        null=True
    )

    class Satus(models.TextChoices):
        RESOLVED = 'RESOLVED', 'Resolved'
        IN_PROGRESS = 'SEEN', 'Seen'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        PENDING = 'PENDING', 'Pending'

    status = models.CharField(
        max_length=10,
        choices=Satus.choices,
        default=Satus.PENDING,
        null=True
    )
    
class RecipeAuditLog(models.Model):
    model_name = models.CharField(max_length=100)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return f'{self.model_name} - {self.field_name} changed by {self.user}'