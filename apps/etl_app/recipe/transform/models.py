from peewee import *
from django.utils import timezone



""" Models """


database_proxy = DatabaseProxy()

class BaseModel(Model):
    class Meta:
        database = database_proxy


class NutritionInformation(BaseModel):
    energy_kcal = CharField()
    energy_perc = CharField()

    fat_g = CharField()
    fat_perc = CharField()

    saturates_g = CharField()
    saturates_perc = CharField()

    carbohydrates_g = CharField()
    carbohydrates_perc = CharField()

    sugars_g = CharField()
    sugars_perc = CharField()

    fiber_g = CharField()

    protein_g = CharField()
    protein_perc = CharField()

    salt_g = CharField()
    salt_perc = CharField()

    class Meta:
        db_table = 'nutrition_information'


class Recipe(BaseModel):
    company = CharField()
    title = CharField(null=False)
    description = CharField(null=False)
    image = CharField(null=True)
    video = CharField(null=True)

    difficulty = CharField(null=True)
    portion_lower = CharField(null=True)
    portion_upper = CharField(null=True)
    portion_units = CharField(null=True)
    time = CharField(null=True)
    time_units = CharField(null=True)

    preparation = BlobField(null=False)
    nutrition_information = ForeignKeyField(NutritionInformation, backref='recipe', null=True, on_delete='CASCADE')

    source_rating = FloatField(null=True)
    source_link = CharField(null=True)

    created_date = DateTimeField(default=timezone.now())
    updated_date = DateTimeField(default=timezone.now())


class Ingredient(BaseModel):
    name = CharField(null=True)

class IngredientQuantity(BaseModel):
    
    quantity_original = CharField(null=False)
    quantity_tempered = CharField(null=False)

    quantity_normalized = FloatField(null=True)
    units_normalized = CharField(null=True)
    extra_quantity = FloatField(null=True)
    extra_units = CharField(null=True)

    ingredient = ForeignKeyField(Ingredient, backref='ingredient_base')
    recipe = ForeignKeyField(Recipe, backref='ingredients', on_delete='CASCADE')

    class Meta:
        db_table = 'ingredient_quantity'
class UsefulTool(BaseModel):
    text = CharField(null=False)
    recipe = ForeignKeyField(Recipe, backref='useful_tools',on_delete='CASCADE')
    
    class Meta:
        db_table = 'useful_tool'

class Tag(BaseModel):
    text = CharField(null=False, unique=True)
    recipe = ManyToManyField(Recipe, backref='tags')


class RecipeLinks(BaseModel):
    link = CharField()
    page = CharField()
    base_search_link = CharField()
    image_link = CharField(null=True)

    class Meta:
        db_table = 'recipe_links'
