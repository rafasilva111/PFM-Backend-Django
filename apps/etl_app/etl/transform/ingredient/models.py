from peewee import *
from playhouse.postgres_ext import PostgresqlExtDatabase, JSONField



""" Models """

database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy
    

class Ingredient(BaseModel):
    # Geral
    title = CharField(default="")
    brand = CharField(default="")
    description = CharField(default="")
    source_link = CharField(default="")
    company = CharField()
    category = JSONField(default=None, null=True)
    
    # Size and Price
    old_size = CharField()
    size = CharField(default=None, null=True)

    portions = FloatField(default=None, null=True)
    portion_size = IntegerField(default=None, null=True)
    portion_unit = IntegerField(default=None, null=True)
    portion_price = FloatField(default=None, null=True)
    
    bulk_price = CharField(default=None, null=True)
    bulk_unit = CharField(default=None, null=True)
    
    size_type = CharField(default=None, null=True)
    minimum_size_for_bulk = IntegerField(default=None, null=True)

    # About the Product
    about_the_product = CharField(default=None, null=True)

    # Caracteristics
    caracteristics = CharField(default=None, null=True)

    # Other Information
    other_information = CharField(default=None, null=True)

    # Nutritional Information
    nutrition_information = CharField(default=None, null=True)
    
    # Legal Info
    legal_info = CharField(default=None, null=True)
    
    # Validation
    is_valid = BooleanField(default=False)
    
class Image(BaseModel):
    path = CharField(unique=True)
    ingredient = ForeignKeyField(Ingredient, backref='images', null=True, on_delete='CASCADE')

class Tag(BaseModel):
    text = CharField(unique=True)
    ingredient = ManyToManyField(Ingredient, backref='tags')


class IngredientLink(BaseModel):
    link = CharField()
    category = CharField()
    page = CharField()
    base_search_link = CharField()

    class Meta:
        db_table = 'ingredient_link'


IngredientTagThrough = Ingredient.tags.get_through_model()