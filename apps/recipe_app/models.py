from django.db import models
from django.db.models import Avg, Count
from apps.user_app.models import User
from apps.common.models import BaseModel
import urllib.parse

###
#   Recipe Models
##

class Ingredient(BaseModel):
    """
    Model to store information about ingredients.
    """
    name = models.CharField(max_length=255)


class IngredientQuantity(BaseModel):
    """
    Model to store quantities of ingredients for recipes.
    """
    ingredient = models.ForeignKey(Ingredient, related_name='ingredient_base', on_delete=models.CASCADE)
    recipe = models.ForeignKey("Recipe", related_name='ingredients', on_delete=models.CASCADE)
    quantity_original = models.CharField(max_length=255)
    quantity_normalized = models.FloatField(null=True)
    units_normalized = models.CharField(null=True, max_length=255)
    extra_quantity = models.FloatField(null=True)
    extra_units = models.CharField(max_length=255, null=True)


class NutritionInformation(BaseModel):
    """
    Model to store nutrition information for recipes.
    """
    energy_kcal = models.FloatField(max_length=255)
    energy_perc = models.FloatField(max_length=255)

    fat_g = models.FloatField(max_length=255)
    fat_perc = models.FloatField(max_length=255)

    saturates_g = models.FloatField(max_length=255)
    saturates_perc = models.FloatField(max_length=255)

    carbohydrates_g = models.FloatField(max_length=255)
    carbohydrates_perc = models.FloatField(max_length=255)

    sugars_g = models.FloatField(max_length=255)
    sugars_perc = models.FloatField(max_length=255)

    fiber_g = models.FloatField(max_length=255)

    protein_g = models.FloatField(max_length=255)
    protein_perc = models.FloatField(max_length=255)

    salt_g = models.FloatField(max_length=255)
    salt_perc = models.FloatField(max_length=255)

    class Meta:
        db_table = 'nutrition_information'


class Recipe(BaseModel):
    title = models.CharField(max_length=255, null=False)
    description = models.TextField( null=False)
    image = models.CharField(max_length=255, null=True)
    video_link = models.CharField(max_length=255, null=True)
    
    company = models.ForeignKey('user_app.Company', related_name='recipes', on_delete=models.CASCADE, null=True)

    difficulty = models.CharField(max_length=255, null=True)
    portion_lower = models.IntegerField(default=0, null=True)
    portion_upper = models.IntegerField(default=0, null=True)
    portion_units = models.CharField(max_length=255, null=True)
    time = models.IntegerField(default=0, null=True)
    
    views = models.IntegerField(default=0, null=False)
    created_by = models.ForeignKey(User, related_name='created_recipes', on_delete=models.CASCADE, null=True)
    nutrition_information = models.OneToOneField(NutritionInformation, related_name='recipe', null=True, on_delete=models.CASCADE)
    rating = models.FloatField(default=0)
    
    source_rating = models.FloatField(null=True)
    source_link = models.CharField(max_length=255, null=True,unique=True)
        
    verified = models.BooleanField(default=False)
    
    is_public = models.BooleanField(default=True, null=False)
    
    users_liked = models.ManyToManyField(User, related_name='liked_recipes', blank=True)
    users_saved = models.ManyToManyField(User, related_name='saved_recipes', blank=True)

    def get_average_rating(self):
        return self.ratings.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0
    
    def get_image_url(self):
        """
        Returns the image URL for the recipe.
        """
        if self.image:
            encoded_path = urllib.parse.quote(self.image, safe='')
            return f"https://firebasestorage.googleapis.com/v0/b/project-food-manager.firebasestorage.app/o/{encoded_path}?alt=media&token=711bb47a-dac0-43ae-82b2-189299641377"
        return None

    @property
    def likes(self):
        return self.users_liked.count()
    
    @property
    def saves(self):
        return self.users_saved.count()
    
    

    class Meta:
        ordering = ['-views']  # Order recipes by views in descending order
        permissions = [
            ("can_view_recipe", "Can view Recipe's details"),
            ("can_view_recipes", "Can view Recipes list"),
            ("can_delete_recipe", "Can delete Recipe"), 
        ]


class Preparation(BaseModel):
    """
    Model to store tags for recipes.
    """
    section = models.CharField(max_length=255, null=True)
    step = models.CharField(max_length=2)
    description = models.TextField()
    recipe = models.ForeignKey(Recipe,on_delete=models.CASCADE, related_name='preparation')


class Tag(BaseModel):
    """
    Model to store tags for recipes.
    """
    text = models.CharField(max_length=30, unique=True)
    recipes = models.ManyToManyField(Recipe, related_name='tags')


class RecipeRating(BaseModel):
    """
    Model to store ratings for recipes.
    """
    recipe = models.ForeignKey(Recipe, related_name='ratings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='rated_recipes', on_delete=models.CASCADE)
    rating = models.IntegerField(null=True)


class UsefulTool(BaseModel):
    """
    Model to store useful tools for recipes.
    """
    text = models.CharField(max_length=255)
    recipes = models.ManyToManyField(Recipe, related_name='useful_tools')


###
#   Recipe Comment
##


class Comment(BaseModel):
    """
    Model to store comments on recipes.
    """
    text = models.CharField(max_length=255)
    recipe = models.ForeignKey(Recipe, related_name='comments', on_delete=models.CASCADE, null=True)
    parent_comment = models.ForeignKey('self', related_name='comments', on_delete=models.CASCADE, null=True)
    likes = models.ManyToManyField(User, related_name='comment_likes')
    user = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)


###
#   Recipe Report
##


class RecipeReport(BaseModel):
    """
    Model to store reports on recipes.
    """
    title = models.CharField(max_length=255)
    message = models.CharField(max_length=255)
    recipe = models.ForeignKey(Recipe, related_name='reports', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='my_recipe_reports', on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(User, related_name='recipe_reports', on_delete=models.CASCADE, null=True)
    
    @property
    def reviewed(self):
        return self.reviewed_by is not None

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

    class Status(models.TextChoices):
        RESOLVED = 'RESOLVED', 'Resolved'
        IN_PROGRESS = 'SEEN', 'Seen'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        PENDING = 'PENDING', 'Pending'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        null=True
    )

    
    class Meta:
        permissions = [
            ("can_view_recipe_report", "Can view Recipe Report's details"),
            ("can_view_recipe_reports", "Can view Recipe Reports list"),
            ("can_create_recipe_report", "Can create Recipe Report"),
            ("can_delete_recipe_report", "Can delete Recipe Report"),
            ("can_review_recipe_report", "Can review Recipe Report"),
            ("can_unreview_recipe_report", "Can unreview Recipe Report"),
        ]

    def review(self, reviewed_by):
        if not reviewed_by:
            raise ValueError("The 'reviewed_by' argument is required.")
        
        self.reviewed_by = reviewed_by
        self.save()
    
    def unreview(self):
        
        self.reviewed_by = None
        self.save()
###
#   Recipe Audit Log
##


class RecipeAuditLogStatusHistory(models.Model):
    """
    Model to store the status history of RecipeAuditLog.
    """
    audit_log = models.ForeignKey('RecipeAuditLog', on_delete=models.CASCADE, related_name='status_history')
    
    class Status(models.TextChoices):
        Accepted = 'ACCEPTED', 'Accepted'
        Unaccepted = 'UNNACCEPTED', 'Unaccepted'
        Reviewed = 'REVIEWED', 'Reviewed'
        Unreviewed = 'UNREVIEWED', 'Unreviewed'

    status = models.CharField(
        max_length=20,
        choices=Status.choices
    )

    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_changes')
    changed_at = models.DateTimeField(auto_now_add=True)


class RecipeAuditLog(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='audit_logs')
    task = models.ForeignKey('etl_app.Task', on_delete=models.CASCADE, related_name='recipe_audit_logs')
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_audit_logs', null=True)
    
    description = models.CharField(max_length=255)
    
    field = models.CharField(max_length=100, null=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    
    reviewed = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)

    def save_status_history(self, changed_by, status):
        RecipeAuditLogStatusHistory.objects.create(
            audit_log=self,
            status=status,
            changed_by=changed_by
        )
    
    def save(self,changed_by = None, *args, **kwargs):
        
        
        " Check if this is a new record or an update, and if so, save the status history "
        " If this is a new record, we don't need to check who changed it"
        if self.pk:  
            
            old_record = RecipeAuditLog.objects.get(pk=self.pk)
            
            if old_record.reviewed != self.reviewed:
                
                if not changed_by:
                    raise ValueError("The 'changed_by' argument is required.")
                
                if self.reviewed:
                    self.save_status_history(changed_by=changed_by, status = RecipeAuditLogStatusHistory.Status.Reviewed)
                else:
                    self.save_status_history(changed_by=changed_by, status = RecipeAuditLogStatusHistory.Status.Unreviewed)
            
            if old_record.accepted != self.accepted:
            
                if not changed_by:
                    raise ValueError("The 'changed_by' argument is required.")
                
                if self.accepted:
                    self.save_status_history(changed_by=changed_by, status = RecipeAuditLogStatusHistory.Status.Accepted)
                else:
                    self.save_status_history(changed_by=changed_by, status = RecipeAuditLogStatusHistory.Status.Unaccepted)

            
                
        
        super().save(*args, **kwargs)

    class Type(models.TextChoices):
        Create = 'Create', 'Create'
        Update = 'Update', 'Update'
        Delete = 'Delete', 'Delete'

    type = models.CharField(
        max_length=20,
        choices=Type.choices
    )
    
    class SubType(models.TextChoices):
        Create = 'Create', 'Create'
        Update = 'Update', 'Update'
        Delete = 'Delete', 'Delete'
        NONE = 'None', 'None'

    sub_type = models.CharField(
        max_length=20,
        choices=SubType.choices,
        default = SubType.NONE
    )
    
    
    class Meta:
        permissions = [
            ("can_view_audit_log", "Can view Audit Log's details"),
            ("can_view_audit_logs", "Can view Audit Logs list"),
            ("can_delete_audit_log", "Can delete Audit Log"),
            ("can_accept_audit_log", "Can accept Audit Log"),
            ("can_unaccept_audit_log", "Can unaccept Audit Log"),
            ("can_review_audit_log", "Can review Audit Log"),
            ("can_unreview_audit_log", "Can unreview Audit Log"),
        ]
    
    def accept(self, changed_by):
        self.accepted = True
        self.reviewed = True
        self.save(changed_by=changed_by)
        
        
        missing_accepted_audit_logs = self.recipe.audit_logs.filter(accepted=False).count()
        
        if missing_accepted_audit_logs == 0:
            self.recipe.verified = True
        else:
            self.recipe.verified = False
            
        self.recipe.save()
        
    def unaccept(self, changed_by):
        self.accepted = False
        self.reviewed = False
        self.recipe.verified = False
        self.recipe.save()
        self.save(changed_by=changed_by)
    
    def review(self, changed_by):
        self.reviewed = True
        self.save(changed_by=changed_by)
    
    def unreview(self, changed_by):
        self.reviewed = False
        self.save(changed_by=changed_by)
    
"""    def delete(self):
        self.recipe.verified = False
        
        match self.type:
            case RecipeAuditLog.Type.Create:
                update_audit_logs = RecipeAuditLog.objects.filter(
                    recipe=self.recipe,
                    task=self.task,
                    type=RecipeAuditLog.Type.Update
                ).count()
                
                if update_audit_logs == 0:
                    super().delete()
                else:
                    raise ValueError("This Create Audit Log cannot be deleted because there are still associated Update Audit Logs.")
                
            case RecipeAuditLog.Type.Update | RecipeAuditLog.Type.Delete:
                super().delete()"""
                
    